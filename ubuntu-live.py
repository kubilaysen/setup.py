#!/bin/bash

# Hata ayıklama modu: Betik çalışırken adımları gösterir ve hata alırsa durur
set -e

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

# Kullanıcıdan gerekli bilgileri al
read -p "Lütfen sunucunuzun alan adını girin (örnek: market.kubilaysen.com): " DOMAIN
read -p "Lütfen MySQL root kullanıcısının mevcut şifresini girin: " -s ROOT_PASSWORD
echo
read -p "Lütfen 'kubi' kullanıcısı için güçlü bir şifre girin: " -s KUBI_PASSWORD
echo
read -p "PrestaShop için PHP'de kullanılacak maksimum dosya yükleme boyutunu girin (örnek: 64M): " UPLOAD_MAX_FILESIZE
read -p "PHP için kullanılacak maksimum post boyutunu girin (örnek: 64M): " POST_MAX_SIZE
read -p "PHP için maksimum yürütme süresini girin (örnek: 300): " MAX_EXECUTION_TIME
read -p "PHP için maksimum giriş değişkenlerini girin (örnek: 10000): " MAX_INPUT_VARS

# Değişkenler
APACHE_CONF="/etc/apache2/sites-available/$DOMAIN.conf"
WEB_ROOT="/var/www/$DOMAIN"

# Sudo yetkilerini doğrula
sudo -v

# Sistem güncellenmesi ve gerekli paketlerin kurulumu
echo "Sistem güncelleniyor ve gerekli paketler yükleniyor..."
sudo apt update && sudo apt upgrade -y
check_success "Sistem güncellemesi"

# Apache'yi kurma
echo "Apache kuruluyor..."
sudo apt install -y apache2
check_success "Apache kurulumu"

# Apache için güvenlik duvarı ayarlarını yapma
echo "Güvenlik duvarı ayarları yapılıyor..."
sudo ufw allow 'Apache Full'
sudo ufw --force enable
check_success "Güvenlik duvarı ayarları"

# MySQL'i kurma
echo "MySQL kuruluyor..."
sudo apt install -y mysql-server
check_success "MySQL kurulumu"

# MySQL root kullanıcısının kimlik doğrulama yöntemini değiştirme
echo "MySQL root kullanıcısının kimlik doğrulama yöntemi kontrol ediliyor..."
AUTH_PLUGIN=$(sudo mysql -u root -p"$ROOT_PASSWORD" -e "SELECT plugin FROM mysql.user WHERE user='root' AND host='localhost';" | tail -n1)

if [ "$AUTH_PLUGIN" != "mysql_native_password" ]; then
    echo "MySQL root kullanıcısının kimlik doğrulama yöntemi mysql_native_password olarak değiştiriliyor..."
    sudo mysql -u root -p"$ROOT_PASSWORD" -e "ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '$ROOT_PASSWORD'; FLUSH PRIVILEGES;"
    check_success "MySQL root kullanıcısının kimlik doğrulama yöntemini değiştirme"
fi

# MySQL güvenlik yapılandırması
echo "MySQL güvenlik yapılandırması yapılıyor..."
sudo mysql_secure_installation <<EOF

y
y
$ROOT_PASSWORD
$ROOT_PASSWORD
y
y
y
y
EOF
check_success "MySQL güvenlik yapılandırması"

# MySQL veritabanı ve kullanıcı ayarları
echo "MySQL veritabanı ve kullanıcı ayarları yapılıyor..."
sudo mysql -u root -p"$ROOT_PASSWORD" <<MYSQL_SCRIPT
DROP DATABASE IF EXISTS prestashop_db;
CREATE DATABASE prestashop_db CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
DROP USER IF EXISTS 'kubi'@'localhost';
CREATE USER 'kubi'@'localhost' IDENTIFIED BY '$KUBI_PASSWORD';
GRANT ALL PRIVILEGES ON prestashop_db.* TO 'kubi'@'localhost';
FLUSH PRIVILEGES;
MYSQL_SCRIPT
check_success "MySQL veritabanı ve kullanıcı ayarları"

# MySQL bağlantısını test etme
echo "MySQL bağlantısını test ediyor..."
mysql -u kubi -p"$KUBI_PASSWORD" -h 127.0.0.1 prestashop_db -e "SELECT DATABASE();"
check_success "MySQL 'kubi' kullanıcısı ile bağlantı testi"

# PHP'yi kurma ve gerekli uzantıları yükleme
echo "PHP kuruluyor ve gerekli uzantılar yükleniyor..."
sudo apt install -y php libapache2-mod-php php-mysql php-curl php-gd php-mbstring php-intl php-xml php-zip php-soap
check_success "PHP ve uzantılar kurulumu"

# PHP ayarlarını yapılandırma
echo "PHP ayarları düzenleniyor..."
PHP_INI="/etc/php/7.4/apache2/php.ini"

sudo sed -i "s/memory_limit = .*/memory_limit = $MEMORY_LIMIT/" $PHP_INI
sudo sed -i "s/upload_max_filesize = .*/upload_max_filesize = $UPLOAD_MAX_FILESIZE/" $PHP_INI
sudo sed -i "s/post_max_size = .*/post_max_size = $POST_MAX_SIZE/" $PHP_INI
sudo sed -i "s/max_execution_time = .*/max_execution_time = $MAX_EXECUTION_TIME/" $PHP_INI
sudo sed -i "s/max_input_vars = .*/max_input_vars = $MAX_INPUT_VARS/" $PHP_INI
sudo sed -i "s/allow_url_fopen = Off/allow_url_fopen = On/" $PHP_INI
check_success "PHP ayarlarının düzenlenmesi"

# Apache için DirectoryIndex sırasını değiştirme
echo "Apache DirectoryIndex sırası değiştiriliyor..."
sudo sed -i 's/DirectoryIndex index.html index.cgi index.pl index.php index.xhtml index.htm/DirectoryIndex index.php index.html index.cgi index.pl index.xhtml index.htm/' /etc/apache2/mods-enabled/dir.conf
check_success "DirectoryIndex sırası değiştirildi"

# Apache'yi yeniden başlatma
echo "Apache yeniden başlatılıyor..."
sudo systemctl restart apache2
check_success "Apache yeniden başlatma"

# phpMyAdmin kurulumu
echo "phpMyAdmin kuruluyor..."
sudo apt install -y phpmyadmin
check_success "phpMyAdmin kurulumu"

# phpMyAdmin Apache ile entegre etme
echo "phpMyAdmin Apache ile entegre ediliyor..."
sudo phpenmod mbstring
sudo systemctl restart apache2
check_success "phpMyAdmin Apache ile entegrasyonu"

# Apache sanal ana bilgisayarını oluşturma
echo "Apache sanal ana bilgisayarı oluşturuluyor..."
sudo mkdir -p $WEB_ROOT
sudo chown -R $USER:$USER $WEB_ROOT

sudo bash -c "cat > $APACHE_CONF <<EOL
<VirtualHost *:80>
    ServerName $DOMAIN
    ServerAlias www.$DOMAIN
    ServerAdmin webmaster@$DOMAIN
    DocumentRoot $WEB_ROOT

    <Directory $WEB_ROOT>
        Options Indexes FollowSymLinks
        AllowOverride All
        Require all granted
    </Directory>

    ErrorLog \${APACHE_LOG_DIR}/error.log
    CustomLog \${APACHE_LOG_DIR}/access.log combined
</VirtualHost>
EOL"

check_success "Apache sanal ana bilgisayarı oluşturma"

# Apache sanal ana bilgisayarını etkinleştirme ve varsayılan siteyi devre dışı bırakma
echo "Apache sanal ana bilgisayarı etkinleştiriliyor ve varsayılan site devre dışı bırakılıyor..."
sudo a2ensite $DOMAIN.conf
sudo a2dissite 000-default.conf
check_success "Apache sanal ana bilgisayarı etkinleştirme ve varsayılan siteyi devre dışı bırakma"

# Apache yapılandırmasını kontrol etme
echo "Apache yapılandırması kontrol ediliyor..."
sudo apache2ctl configtest
check_success "Apache yapılandırma testi"

# Apache'yi yeniden yükleme
echo "Apache yeniden yükleniyor..."
sudo systemctl reload apache2
check_success "Apache yeniden yükleme"

# PrestaShop'u indirme ve kurma
echo "PrestaShop indiriliyor ve kuruluyor..."
cd /tmp

# PrestaShop'un en son sürümünü dinamik olarak tespit etme
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
sudo mkdir -p $WEB_ROOT
sudo unzip -o prestashop_latest.zip -d $WEB_ROOT
check_success "PrestaShop dosyalarını çıkarma"

# Dosya izinlerini ayarlama
echo "PrestaShop dosya izinleri ayarlanıyor..."
sudo chown -R www-data:www-data $WEB_ROOT
sudo find $WEB_ROOT -type d -exec chmod 755 {} \;
sudo find $WEB_ROOT -type f -exec chmod 644 {} \;
check_success "PrestaShop dosya izinlerini ayarlama"

# .htaccess dosyasını etkinleştirme
echo "Apache için .htaccess dosyasını etkinleştiriliyor..."
sudo a2enmod rewrite
sudo systemctl restart apache2
check_success ".htaccess modülü etkinleştirme ve Apache yeniden başlatma"

# PrestaShop için Apache sanal ana bilgisayarını güncelleme
echo "PrestaShop için Apache sanal ana bilgisayarı güncelleniyor..."
sudo bash -c "cat >> $APACHE_CONF <<EOL

# Allow .htaccess Overrides
<Directory $WEB_ROOT>
    AllowOverride All
</Directory>
EOL"

# Apache'yi yeniden yükleme
sudo systemctl reload apache2
check_success "Apache yeniden yükleme"

# phpMyAdmin kurulumu ve yapılandırması
echo "phpMyAdmin kuruluyor ve yapılandırılıyor..."
sudo apt install -y phpmyadmin
check_success "phpMyAdmin kurulumu"

# phpMyAdmin için Apache yapılandırmasını etkinleştirme
echo "phpMyAdmin Apache ile entegre ediliyor..."
sudo phpenmod mbstring
sudo systemctl restart apache2
check_success "phpMyAdmin Apache ile entegrasyonu"

# Test PHP işleme
echo "PHP işleme testi yapılıyor..."
echo "<?php phpinfo(); ?>" > $WEB_ROOT/info.php
check_success "PHP info.php dosyası oluşturma"

echo "Lütfen tarayıcınızda http://$DOMAIN/info.php adresine gidin ve PHP'nin düzgün çalıştığını doğrulayın."
echo "Eğer doğru çalışıyorsa, info.php dosyasını silmek için aşağıdaki komutu kullanabilirsiniz:"
echo "sudo rm $WEB_ROOT/info.php"

# phpMyAdmin için güvenlik ayarları (Opsiyonel)
read -p "phpMyAdmin'e ek güvenlik önlemleri eklemek istiyor musunuz? [y/N]: " phpmyadmin_security
if [[ "$phpmyadmin_security" =~ ^[Yy]$ ]]; then
    echo "phpMyAdmin'e ek güvenlik önlemleri ekleniyor..."
    sudo sed -i "s/Require all granted/Require ip YOUR_IP_ADDRESS/" /etc/apache2/conf-available/phpmyadmin.conf
    sudo systemctl reload apache2
    check_success "phpMyAdmin güvenlik ayarları"
    echo "phpMyAdmin'e sadece belirtilen IP adresinden erişim sağlanacaktır."
fi

# PrestaShop kurulum sihirbazını tamamlama
echo "PrestaShop kurulumu tamamlandı."
echo "Tarayıcınızdan http://$DOMAIN/install adresine giderek PrestaShop kurulum sihirbazını tamamlayın."
echo "Kurulum sırasında aşağıdaki veritabanı bilgilerini kullanın:"
echo "-------------------------------------------"
echo "Database server address: 127.0.0.1"
echo "Database name: prestashop_db"
echo "Database login: kubi"
echo "Database password: [Belirlediğiniz Şifre]"
echo "Tables prefix: ps_"
echo "-------------------------------------------"
echo "Kurulum tamamlandıktan sonra güvenlik için 'install' klasörünü silmeyi unutmayın:"
echo "sudo rm -rf $WEB_ROOT/install"

# Ekstra: Swap alanı oluşturma (Opsiyonel)
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

echo "LAMP stack kurulumu tamamlandı! Her şeyin düzgün çalıştığını doğrulamak için yukarıdaki adımları takip edin."
