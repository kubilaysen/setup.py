#!/bin/bash

# Hata ayıklama modu: Betik çalışırken adımları gösterir ve hata alırsa durur
set -ex

# Fonksiyon: Hata kontrolü
check_success() {
    if [ $? -ne 0 ]; then
        echo "Hata: $1 başarısız oldu!" >&2
        exit 1
    fi
}

# Fonksiyon: DNS Kaydı Kontrolü (A ve CNAME kayıtlarını kontrol eder)
check_dns() {
    DOMAIN=$1
    RECORD_TYPE=$2
    EXPECTED_IP=$3

    echo "DNS kontrolü: $DOMAIN ($RECORD_TYPE)"
    RESOLVED_IP=$(dig +short $DOMAIN $RECORD_TYPE)

    if [ -z "$RESOLVED_IP" ]; then
        # CNAME kontrolü
        CNAME=$(dig +short $DOMAIN CNAME)
        if [ -z "$CNAME" ]; then
            echo "Hata: $DOMAIN için $RECORD_TYPE kaydı bulunamadı ve CNAME kaydı mevcut değil."
            return 1
        else
            echo "$DOMAIN için CNAME kaydı mevcut: $CNAME"
            # CNAME hedefinin A kaydını çöz
            RESOLVED_IP=$(dig +short $CNAME A)
            if [ -z "$RESOLVED_IP" ]; then
                echo "Hata: $CNAME için A kaydı bulunamadı."
                return 1
            else
                echo "$CNAME için A kaydı mevcut: $RESOLVED_IP"
                # Beklenen IP ile karşılaştır
                if [ "$RESOLVED_IP" != "$EXPECTED_IP" ]; then
                    echo "Hata: $CNAME için A kaydı beklenen IP ile eşleşmiyor."
                    return 1
                fi
            fi
        fi
    else
        echo "$DOMAIN için $RECORD_TYPE kaydı mevcut: $RESOLVED_IP"
        # Beklenen IP ile karşılaştır
        if [ "$RESOLVED_IP" != "$EXPECTED_IP" ]; then
            echo "Hata: $DOMAIN için $RECORD_TYPE kaydı beklenen IP ile eşleşmiyor."
            return 1
        fi
    fi

    return 0
}

# Kullanıcıdan sudo şifresini başta bir kez istemek için
sudo -v

# Sistem güncellenmesi ve gerekli paketlerin kurulumu
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

# PHP 7.2 Kurulumu ve Ayarları
echo "PHP 7.2 kuruluyor..."
sudo apt install -y php7.2 libapache2-mod-php7.2 \
    php7.2-mysql php7.2-curl php7.2-gd \
    php7.2-mbstring php7.2-intl php7.2-xml \
    php7.2-zip php7.2-soap php7.2-cli \
    php7.2-common php7.2-opcache \
    php7.2-readline unzip curl git
check_success "PHP 7.2 ve gerekli uzantıların kurulumu"

# Gerekli PHP uzantılarının etkinleştirilmesi
echo "Gerekli PHP uzantıları etkinleştiriliyor..."
sudo phpenmod -v 7.2 mbstring
sudo phpenmod -v 7.2 intl
sudo phpenmod -v 7.2 gd
sudo phpenmod -v 7.2 curl
sudo phpenmod -v 7.2 zip
sudo phpenmod -v 7.2 xml
sudo phpenmod -v 7.2 soap
sudo phpenmod -v 7.2 opcache
check_success "PHP uzantılarını etkinleştirme"

# Apache için gerekli modüllerin etkinleştirilmesi
echo "Apache için gerekli modüller etkinleştiriliyor..."
sudo a2enmod rewrite
sudo a2enmod ssl
check_success "Apache modüllerini etkinleştirme"

# Apache'yi PHP 7.2 ile yeniden başlatma
echo "Apache yeniden başlatılıyor ve PHP 7.2 ile çalıştırılıyor..."
sudo a2dismod php8.1 || true  # Eğer PHP 8.1 etkinse devre dışı bırak
sudo a2enmod php7.2
sudo systemctl restart apache2
check_success "Apache yeniden başlatma ve PHP 7.2 ile çalıştırma"

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
    echo "HATA: Composer checksum doğrulaması başarısız oldu!" >&2
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
read -s root_password

# Root kullanıcısının kimlik doğrulama yöntemini kontrol et ve gerekirse değiştir
echo "MySQL root kullanıcısının kimlik doğrulama yöntemi kontrol ediliyor..."
AUTH_PLUGIN=$(sudo mysql -u root -p"$root_password" -e "SELECT plugin FROM mysql.user WHERE user='root' AND host='localhost';" | tail -n1)

if [ "$AUTH_PLUGIN" != "mysql_native_password" ]; then
    echo "MySQL root kullanıcısının kimlik doğrulama yöntemi mysql_native_password olarak değiştiriliyor..."
    sudo mysql -u root -p"$root_password" -e "ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'YeniRootSifresi'; FLUSH PRIVILEGES;"
    check_success "MySQL root kullanıcısının kimlik doğrulama yöntemini değiştirme"
fi

# 'kubi' kullanıcısı ve veritabanını oluşturma
sudo mysql -u root -p"$root_password" <<MYSQL_SCRIPT
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
PHP_INI="/etc/php/7.2/apache2/php.ini"

sudo sed -i 's/memory_limit = .*/memory_limit = 256M/' $PHP_INI
sudo sed -i 's/upload_max_filesize = .*/upload_max_filesize = 64M/' $PHP_INI
sudo sed -i 's/post_max_size = .*/post_max_size = 64M/' $PHP_INI
sudo sed -i 's/max_execution_time = .*/max_execution_time = 300/' $PHP_INI
sudo sed -i 's/max_input_vars = .*/max_input_vars = 10000/' $PHP_INI
sudo sed -i 's/allow_url_fopen = Off/allow_url_fopen = On/' $PHP_INI
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
    # DNS kayıtlarının kontrol edilmesi
    echo "DNS kayıtları kontrol ediliyor..."
    check_dns "market.kubilaysen.com" "A" "212.64.217.151" || exit 1
    check_dns "www.market.kubilaysen.com" "A" "212.64.217.151" || exit 1

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

# PrestaShop'un en son sürümünü dinamik olarak tespit edin
PRESTASHOP_VERSION=$(curl -s https://api.github.com/repos/PrestaShop/PrestaShop/releases/latest | grep tag_name | cut -d '"' -f4)

if [ -z "$PRESTASHOP_VERSION" ]; then
    echo "Hata: En son PrestaShop sürümü bulunamadı." >&2
    exit 1
fi

echo "Bulunan en son PrestaShop sürümü: $PRESTASHOP_VERSION"

# Etiketin 'v' ile başlamadığını kontrol et ve uygun şekilde işleme al
if [[ "$PRESTASHOP_VERSION" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    # Etiket 'v' ile başlıyorsa, 'v' önekini kaldır
    VERSION="${PRESTASHOP_VERSION#v}"
    PRESTASHOP_URL="https://github.com/PrestaShop/PrestaShop/releases/download/${PRESTASHOP_VERSION}/prestashop_${VERSION}.zip"
elif [[ "$PRESTASHOP_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    # Etiket 'v' ile başlamıyorsa, doğrudan sürüm numarasını kullan
    VERSION="$PRESTASHOP_VERSION"
    PRESTASHOP_URL="https://github.com/PrestaShop/PrestaShop/releases/download/${PRESTASHOP_VERSION}/prestashop_${VERSION}.zip"
else
    echo "Hata: PrestaShop sürüm etiketi beklenen formatta değil." >&2
    exit 1
fi

# PrestaShop'u indir
wget "$PRESTASHOP_URL" -O prestashop_latest.zip
check_success "PrestaShop sürümünü indirme"

# PrestaShop dosyalarını çıkarma
sudo unzip -o prestashop_latest.zip -d /var/www/html/prestashop
check_success "PrestaShop dosyalarını çıkarma"

# Dosya izinlerini ayarlama
sudo chown -R www-data:www-data /var/www/html/prestashop
sudo chmod -R 755 /var/www/html/prestashop
check_success "PrestaShop dosya izinlerini ayarlama"

# config/defines.inc.php dosyasını düzenleme (Türkçe dil hatası için)
echo "config/defines.inc.php dosyası düzenleniyor..."
CONFIG_FILE="/var/www/html/prestashop/config/defines.inc.php"

if [ -f "$CONFIG_FILE" ]; then
    sudo sed -i 's/^define.*LCTYPE_.*$/\/\/&/' "$CONFIG_FILE"
    check_success "config/defines.inc.php dosyasını düzenleme"
else
    echo "Hata: $CONFIG_FILE dosyası bulunamadı." >&2
    exit 1
fi

# /var/cache/prod dizinini temizleme (Klasörü silme!)
echo "/var/cache/prod dizini temizleniyor..."
CACHE_DIR="/var/www/html/prestashop/var/cache/prod"

if [ -d "$CACHE_DIR" ]; then
    sudo rm -rf ${CACHE_DIR:?}/*
    check_success "/var/cache/prod dizinini temizleme"
else
    echo "Uyarı: $CACHE_DIR dizini bulunamadı. Devam ediliyor..."
fi

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

# PrestaShop Kurulum Sihirbazını Tamamlama
echo "Kurulum tamamlandı."
echo "Tarayıcınızdan http://market.kubilaysen.com/install veya https://market.kubilaysen.com/install adresine giderek PrestaShop kurulum sihirbazını tamamlayın."
echo "Kurulum sihirbazında Türkçe dilini seçmeyi unutmayın."
echo "Ayrıca phpMyAdmin'e erişmek için http://market.kubilaysen.com/phpmyadmin veya https://market.kubilaysen.com/phpmyadmin adresini kullanabilirsiniz."
echo "PrestaShop kurulumunu tamamladıktan sonra güvenlik için 'install' klasörünü silmeyi unutmayın:"
echo "sudo rm -rf /var/www/html/prestashop/install"
