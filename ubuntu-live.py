#!/bin/bash

# Kullanıcıdan sudo şifresini başta bir kez istemek için
sudo -v

# Sistem güncellemesi ve gerekli paketlerin kurulumu
echo "Sistem güncelleniyor ve gerekli paketler yükleniyor..."
sudo apt update && sudo apt upgrade -y
sudo apt install -y apache2 mysql-server php libapache2-mod-php php-mysql php-curl php-gd php-mbstring php-intl php-xml php-zip php-soap unzip

# MySQL veritabanı ve kullanıcı ayarları
echo "MySQL veritabanı ve kullanıcı oluşturuluyor..."
sudo mysql -u root <<MYSQL_SCRIPT
CREATE DATABASE prestashop CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
CREATE USER 'prestashop_user'@'localhost' IDENTIFIED BY 'password';
GRANT ALL PRIVILEGES ON prestashop.* TO 'prestashop_user'@'localhost';
FLUSH PRIVILEGES;
MYSQL_SCRIPT

# PHP ayarlarının yapılması
echo "PHP ayarları düzenleniyor..."
sudo sed -i 's/memory_limit = .*/memory_limit = 256M/' /etc/php/8.1/apache2/php.ini
sudo sed -i 's/upload_max_filesize = .*/upload_max_filesize = 64M/' /etc/php/8.1/apache2/php.ini
sudo sed -i 's/post_max_size = .*/post_max_size = 64M/' /etc/php/8.1/apache2/php.ini
sudo sed -i 's/max_execution_time = .*/max_execution_time = 300/' /etc/php/8.1/apache2/php.ini
sudo sed -i 's/max_input_vars = .*/max_input_vars = 10000/' /etc/php/8.1/apache2/php.ini

# Apache yapılandırması
echo "Apache yapılandırması yapılıyor..."
sudo bash -c 'cat > /etc/apache2/sites-available/prestashop.conf <<EOL
<VirtualHost *:80>
    ServerName your_domain_or_ip
    DocumentRoot /var/www/html/prestashop

    <Directory /var/www/html/prestashop>
        Options Indexes FollowSymLinks
        AllowOverride All
        Require all granted
    </Directory>

    ErrorLog \${APACHE_LOG_DIR}/error.log
    CustomLog \${APACHE_LOG_DIR}/access.log combined
</VirtualHost>
EOL'

sudo a2ensite prestashop.conf
sudo a2enmod rewrite
sudo systemctl restart apache2

# PrestaShop'u İndirme ve Kurma
echo "PrestaShop indiriliyor ve kuruluyor..."
cd /tmp
wget https://download.prestashop.com/download/releases/prestashop_8.1.zip
sudo unzip prestashop_8.1.zip -d /var/www/html/prestashop
sudo chown -R www-data:www-data /var/www/html/prestashop
sudo chmod -R 755 /var/www/html/prestashop

# Kurulum tamamlandıktan sonra "install" klasörünü kaldırmak için kullanıcıya hatırlatma
echo "Kurulum tamamlandı. Tarayıcınızdan http://your_domain_or_ip adresine giderek PrestaShop kurulumunu tamamlayın."
echo "Kurulum bittikten sonra 'install' klasörünü silmeyi unutmayın: sudo rm -rf /var/www/html/prestashop/install"
