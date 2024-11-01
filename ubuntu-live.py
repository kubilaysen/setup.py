#!/bin/bash

# Hata ayıklama modu: Betik herhangi bir hata ile karşılaştığında durur
set -e

# Fonksiyon: Hata kontrolü
check_success() {
    if [ $? -ne 0 ]; then
        echo "Hata: $1 başarısız oldu!" >&2
        exit 1
    fi
}

# Kullanıcıdan sudo şifresini başta bir kez istemek için
sudo -v

# Sistem güncellemesi ve gerekli paketlerin kurulumu
echo "Sistem güncelleniyor ve gerekli paketler yükleniyor..."
sudo apt update && sudo apt upgrade -y
check_success "Sistem güncellemesi"

# Mevcut Apache, PHP, MySQL ve phpMyAdmin kurulumlarını kaldırma
echo "Mevcut Apache, PHP, MySQL ve phpMyAdmin kurulumları temizleniyor..."

# Apache'yi durdur ve kaldır
sudo systemctl stop apache2 || true
sudo a2dissite *.conf || true
sudo apt purge -y apache2 apache2-utils apache2-bin apache2.2-common || true
sudo apt autoremove -y
check_success "Apache kaldırma"

# PHP'yi kaldır
sudo apt purge -y 'php*' || true
sudo apt autoremove -y
check_success "PHP kaldırma"

# MySQL'i kaldır
sudo systemctl stop mysql || true
sudo apt purge -y mysql-server mysql-client mysql-common || true
sudo rm -rf /etc/mysql /var/lib/mysql
sudo apt autoremove -y
check_success "MySQL kaldırma"

# phpMyAdmin'i kaldır
sudo apt purge -y phpmyadmin || true
sudo rm -rf /usr/share/phpmyadmin
sudo rm -rf /etc/phpmyadmin
sudo rm -rf /var/lib/phpmyadmin
check_success "phpMyAdmin kaldırma"

# Gereksiz paketleri temizleme
sudo apt autoremove -y
sudo apt autoclean -y
check_success "Gereksiz paketleri temizleme"

# PHP PPA'sını ekleyerek en son PHP sürümlerine erişim sağlamak
echo "Ondřej Surý PPA'sı ekleniyor..."
sudo apt install -y software-properties-common
sudo locale-gen C.UTF-8
sudo update-locale LANG=C.UTF-8
sudo add-apt-repository ppa:ondrej/php -y
sudo apt update
check_success "PHP PPA'sı ekleme"

# Gerekli PHP sürümünü belirleme (8.1 veya daha üstü)
PHP_VERSION=8.1
echo "PHP $PHP_VERSION kuruluyor..."
sudo apt install -y php$PHP_VERSION libapache2-mod-php$PHP_VERSION \
    php$PHP_VERSION-mysql php$PHP_VERSION-curl php$PHP_VERSION-gd \
    php$PHP_VERSION-mbstring php$PHP_VERSION-intl php$PHP_VERSION-xml \
    php$PHP_VERSION-zip php$PHP_VERSION-soap php$PHP_VERSION-cli \
    php$PHP_VERSION-common php$PHP_VERSION-opcache \
    php$PHP_VERSION-readline unzip curl git
check_success "PHP $PHP_VERSION ve gerekli uzantıların kurulumu"

# Gerekli PHP uzantılarının etkinleştirilmesi
echo "Gerekli PHP uzantıları etkinleştiriliyor..."
sudo phpenmod -v $PHP_VERSION mbstring
sudo phpenmod -v $PHP_VERSION intl
sudo phpenmod -v $PHP_VERSION gd
sudo phpenmod -v $PHP_VERSION curl
sudo phpenmod -v $PHP_VERSION zip
sudo phpenmod -v $PHP_VERSION xml
sudo phpenmod -v $PHP_VERSION soap
sudo phpenmod -v $PHP_VERSION opcache
check_success "PHP uzantılarını etkinleştirme"

# Apache için gerekli modüllerin etkinleştirilmesi
echo "Apache için gerekli modüller etkinleştiriliyor..."
sudo a2enmod rewrite
sudo a2enmod ssl
check_success "Apache modüllerini etkinleştirme"

# Apache'yi yeniden başlatma
echo "Apache yeniden başlatılıyor..."
sudo systemctl restart apache2
check_success "Apache yeniden başlatma"

# Composer kurulumu
echo "Composer kuruluyor..."
EXPECTED_CHECKSUM="$(wget -q -O - https://composer.github.io/installer.sig)"
php -r "copy('https://getcomposer.org/installer', 'composer-setup.php');"
ACTUAL_CHECKSUM="$(php -r "echo hash_file('sha384', 'composer-setup.php');")"

if [ "$EXPECTED_CHECKSUM" = "$ACTUAL_CHECKSUM" ]; then
    sudo php composer-setup.php --install-dir=/usr/local/bin --filename=composer
    rm composer-setup.php
    echo "Composer başarıyla yüklendi."
else
    echo "ERROR: Composer checksum doğrulaması başarısız oldu!" >&2
    rm composer-setup.php
    exit 1
fi
check_success "Composer kurulumu"

# MySQL kurulumu ve yapılandırması
echo "MySQL kuruluyor..."
sudo apt install -y mysql-server
check_success "MySQL kurulumu"

echo "MySQL güvenlik yapılandırması yapılıyor..."
sudo mysql_secure_installation
# Not: Bu adım interaktiftir ve kullanıcıdan çeşitli güvenlik ayarları için onay istenir.

# MySQL veritabanı ve kullanıcı ayarları
echo "MySQL veritabanı ve kullanıcı ayarları yapılıyor..."
echo "Lütfen MySQL root şifrenizi girin:"
sudo mysql -u root -p <<MYSQL_SCRIPT
DROP DATABASE IF EXISTS prestashop_db;
CREATE DATABASE prestashop_db CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
DROP USER IF EXISTS 'kubi'@'localhost';
CREATE USER 'kubi'@'localhost' IDENTIFIED BY 'Ks856985.,';
GRANT ALL PRIVILEGES ON prestashop_db.* TO 'kubi'@'localhost';
FLUSH PRIVILEGES;
MYSQL_SCRIPT
check_success "MySQL veritabanı ve kullanıcı ayarları"

# PHP ayarlarının yapılması
echo "PHP ayarları düzenleniyor..."
PHP_INI="/etc/php/$PHP_VERSION/apache2/php.ini"

sudo sed -i 's/memory_limit = .*/memory_limit = 256M/' $PHP_INI
sudo sed -i 's/upload_max_filesize = .*/upload_max_filesize = 64M/' $PHP_INI
sudo sed -i 's/post_max_size = .*/post_max_size = 64M/' $PHP_INI
sudo sed -i 's/max_execution_time = .*/max_execution_time = 300/' $PHP_INI
sudo sed -i 's/max_input_vars = .*/max_input_vars = 10000/' $PHP_INI
check_success "PHP ayarlarının düzenlenmesi"

# Apache yapılandırması
echo "Apache yapılandırması yapılıyor..."
sudo bash -c 'cat > /etc/apache2/sites-available/prestashop.conf <<EOL
<VirtualHost *:80>
    ServerName market.kubilaysen.com
    ServerAlias www.market.kubilaysen.com
    DocumentRoot /var/www/html/prestashop

    <Directory /var/www/html/prestashop>
        Options Indexes FollowSymLinks
        AllowOverride All
        Require all granted
    </Directory>

    ErrorLog ${APACHE_LOG_DIR}/prestashop_error.log
    CustomLog ${APACHE_LOG_DIR}/prestashop_access.log combined
</VirtualHost>
EOL'
check_success "Apache sanal ana bilgisayar yapılandırması"

# PrestaShop için Apache sanal ana bilgisayarını etkinleştirme ve Apache'yi yeniden başlatma
sudo a2ensite prestashop.conf
sudo systemctl reload apache2
check_success "Apache yapılandırmasını etkinleştirme ve yeniden yükleme"

# HTTPS için Let's Encrypt kurulumu (Opsiyonel)
read -p "HTTPS (SSL) kurulumu yapmak istiyor musunuz? [y/N]: " ssl_choice
if [[ "$ssl_choice" =~ ^[Yy]$ ]]; then
    echo "Certbot kuruluyor..."
    sudo apt install -y certbot python3-certbot-apache
    check_success "Certbot kurulumu"

    # Kullanıcıdan geçerli bir e-posta adresi girmesini isteyin
    read -p "Lütfen SSL sertifikası için geçerli bir e-posta adresi girin: " user_email
    if [[ ! "$user_email" =~ ^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$ ]]; then
        echo "Hata: Geçersiz bir e-posta adresi girdiniz." >&2
        exit 1
    fi

    echo "SSL sertifikası alınıyor..."
    sudo certbot --apache -d market.kubilaysen.com -d www.market.kubilaysen.com --non-interactive --agree-tos -m "$user_email" --redirect
    check_success "SSL sertifikası kurulumu"
    echo "SSL kurulumu tamamlandı."
fi

# PrestaShop'u İndirme ve Kurma
echo "PrestaShop indiriliyor ve kuruluyor..."
cd /tmp
PRESTASHOP_VERSION=$(curl -s https://api.github.com/repos/PrestaShop/PrestaShop/releases/latest | grep tag_name | cut -d '"' -f4)

# Resmi PrestaShop download linkini kullanın
PRESTASHOP_URL="https://download.prestashop.com/download/releases/prestashop_${PRESTASHOP_VERSION}.zip"
wget "$PRESTASHOP_URL" -O prestashop_latest.zip
check_success "PrestaShop sürümünü indirme"

sudo unzip -o prestashop_latest.zip -d /var/www/html/prestashop
check_success "PrestaShop dosyalarını çıkarma"

sudo chown -R www-data:www-data /var/www/html/prestashop
sudo chmod -R 755 /var/www/html/prestashop
check_success "PrestaShop dosya izinlerini ayarlama"

# Composer ile bağımlılıkların yüklenmesi (Bu adımı kaldırabilirsiniz çünkü resmi paket bağımlılıkları içerir)
# echo "PrestaShop bağımlılıkları yükleniyor..."
# cd /var/www/html/prestashop
# sudo -u www-data composer install --no-dev
# check_success "Composer bağımlılıklarını yükleme"

# phpMyAdmin kurulumu
echo "phpMyAdmin kuruluyor..."
cd /tmp
wget https://www.phpmyadmin.net/downloads/phpMyAdmin-latest-all-languages.zip
check_success "phpMyAdmin indirme"

sudo unzip -o phpMyAdmin-latest-all-languages.zip -d /usr/share
check_success "phpMyAdmin dosyalarını çıkarma"

sudo mv /usr/share/phpMyAdmin-*-all-languages /usr/share/phpmyadmin
sudo mkdir -p /usr/share/phpmyadmin/tmp
sudo chown -R www-data:www-data /usr/share/phpmyadmin
sudo chmod 777 /usr/share/phpmyadmin/tmp
check_success "phpMyAdmin yapılandırması ve izinleri ayarlama"

# phpMyAdmin Apache yapılandırması
echo "phpMyAdmin Apache yapılandırması yapılıyor..."
sudo bash -c 'cat > /etc/apache2/conf-available/phpmyadmin.conf <<EOL
Alias /phpmyadmin /usr/share/phpmyadmin

<Directory /usr/share/phpmyadmin>
    Options Indexes FollowSymLinks
    AllowOverride All
    Require all granted
</Directory>

<Directory /usr/share/phpmyadmin/setup>
   <IfModule mod_authz_core.c>
       <RequireAny>
           Require all granted
       </RequireAny>
   </IfModule>
</Directory>
EOL'
check_success "phpMyAdmin Apache yapılandırması"

sudo a2enconf phpmyadmin
sudo systemctl reload apache2
check_success "phpMyAdmin yapılandırmasını etkinleştirme ve yeniden yükleme"

# Gerekli dizin izinlerinin ayarlanması
echo "Geçici dosya dizin izinleri ayarlanıyor..."
sudo mkdir -p /var/www/html/prestashop/var/cache /var/www/html/prestashop/var/logs
sudo chown -R www-data:www-data /var/www/html/prestashop/var
sudo chmod -R 755 /var/www/html/prestashop/var
check_success "PrestaShop var dizin izinlerini ayarlama"

# Firewall ayarları (UFW kullanılıyorsa)
echo "Firewall ayarları yapılandırılıyor..."
sudo ufw allow 'Apache Full'
echo "Firewall aktif ediliyor..."
sudo ufw --force enable
check_success "Firewall ayarları ve aktif etme"

# Swap Alanı Oluşturma (Opsiyonel)
read -p "Sunucuda yeterli RAM yoksa swap alanı oluşturmak istiyor musunuz? [y/N]: " swap_choice
if [[ "$swap_choice" =~ ^[Yy]$ ]]; then
    echo "Swap alanı oluşturuluyor..."
    sudo fallocate -l 2G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
    echo "Swap alanı oluşturuldu ve etkinleştirildi."
fi

# Kurulum tamamlandıktan sonra "install" klasörünü kaldırmak için kullanıcıya hatırlatma
echo "Kurulum tamamlandı."
echo "Tarayıcınızdan http://market.kubilaysen.com/install veya https://market.kubilaysen.com/install adresine giderek PrestaShop kurulum sihirbazını tamamlayın."
echo "Ayrıca phpMyAdmin'e erişmek için http://market.kubilaysen.com/phpmyadmin veya https://market.kubilaysen.com/phpmyadmin adresini kullanabilirsiniz."
echo "PrestaShop kurulumunu tamamladıktan sonra 'install' klasörünü silmeyi unutmayın:"
echo "sudo rm -rf /var/www/html/prestashop/install"
