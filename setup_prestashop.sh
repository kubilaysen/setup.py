#!/bin/bash

# Sistemi güncelleyin
sudo apt update && sudo apt upgrade -y

# Apache web sunucusunu kurun
sudo apt install apache2 -y

# Gerekli Apache modüllerini etkinleştirin
sudo a2enmod rewrite
sudo a2enmod ssl

# PHP ve gerekli uzantıları kurun
sudo apt install php libapache2-mod-php php-mysql php-gd php-curl php-xml php-zip php-mbstring php-intl php-soap php-xmlrpc php-json -y

# MySQL sunucusunu kurun
sudo apt install mysql-server -y

# MySQL root şifresini ayarlayın ve güvenliği artırın
sudo mysql <<EOF
ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'Ks856985.,';
DELETE FROM mysql.user WHERE User='';
DROP DATABASE IF EXISTS test;
FLUSH PRIVILEGES;
EOF

# PHP ayarlarını düzenleyin
sudo sed -i 's/memory_limit = .*/memory_limit = 256M/' /etc/php/*/apache2/php.ini
sudo sed -i 's/max_execution_time = .*/max_execution_time = 300/' /etc/php/*/apache2/php.ini
sudo sed -i 's/upload_max_filesize = .*/upload_max_filesize = 64M/' /etc/php/*/apache2/php.ini
sudo sed -i 's/max_input_vars = .*/max_input_vars = 10000/' /etc/php/*/apache2/php.ini
sudo sed -i 's/;date.timezone =.*/date.timezone = Europe\/Istanbul/' /etc/php/*/apache2/php.ini

# Web siteleri için dizinler oluşturun
sudo mkdir -p /var/www/www.kubilaysen.com/public_html
sudo mkdir -p /var/www/casaos.kubilaysen.com/public_html
sudo mkdir -p /var/www/market.kubilaysen.com/public_html

# Yetkileri ayarlayın
sudo chown -R $USER:$USER /var/www/*

# www.kubilaysen.com için örnek index.html oluşturun
echo "<html><head><title>www.kubilaysen.com</title></head><body><h1>www.kubilaysen.com'a Hoş Geldiniz</h1></body></html>" > /var/www/www.kubilaysen.com/public_html/index.html

# casaos.kubilaysen.com için örnek index.html oluşturun
echo "<html><head><title>casaos.kubilaysen.com</title></head><body><h1>casaos.kubilaysen.com'a Hoş Geldiniz</h1></body></html>" > /var/www/casaos.kubilaysen.com/public_html/index.html

# Apache Sanal Hostlarını yapılandırın

# www.kubilaysen.com
sudo cat <<EOT > /etc/apache2/sites-available/www.kubilaysen.com.conf
<VirtualHost *:80>
    ServerName www.kubilaysen.com
    DocumentRoot /var/www/www.kubilaysen.com/public_html
    <Directory /var/www/www.kubilaysen.com/public_html>
        Options Indexes FollowSymLinks
        AllowOverride All
        Require all granted
    </Directory>
    ErrorLog \${APACHE_LOG_DIR}/www.kubilaysen.com_error.log
    CustomLog \${APACHE_LOG_DIR}/www.kubilaysen.com_access.log combined
</VirtualHost>
EOT

# casaos.kubilaysen.com
sudo cat <<EOT > /etc/apache2/sites-available/casaos.kubilaysen.com.conf
<VirtualHost *:80>
    ServerName casaos.kubilaysen.com
    DocumentRoot /var/www/casaos.kubilaysen.com/public_html
    <Directory /var/www/casaos.kubilaysen.com/public_html>
        Options Indexes FollowSymLinks
        AllowOverride All
        Require all granted
    </Directory>
    ErrorLog \${APACHE_LOG_DIR}/casaos.kubilaysen.com_error.log
    CustomLog \${APACHE_LOG_DIR}/casaos.kubilaysen.com_access.log combined
</VirtualHost>
EOT

# market.kubilaysen.com
sudo cat <<EOT > /etc/apache2/sites-available/market.kubilaysen.com.conf
<VirtualHost *:80>
    ServerName market.kubilaysen.com
    DocumentRoot /var/www/market.kubilaysen.com/public_html
    <Directory /var/www/market.kubilaysen.com/public_html>
        Options Indexes FollowSymLinks
        AllowOverride All
        Require all granted
    </Directory>
    ErrorLog \${APACHE_LOG_DIR}/market.kubilaysen.com_error.log
    CustomLog \${APACHE_LOG_DIR}/market.kubilaysen.com_access.log combined
</VirtualHost>
EOT

# Yeni sanal hostları etkinleştirin
sudo a2ensite www.kubilaysen.com.conf
sudo a2ensite casaos.kubilaysen.com.conf
sudo a2ensite market.kubilaysen.com.conf

# Varsayılan siteyi devre dışı bırakın
sudo a2dissite 000-default.conf

# Apache'yi yeniden başlatın
sudo systemctl restart apache2

# PrestaShop için MySQL veritabanı oluşturun
DBNAME='prestashop_db'
DBUSER='kubi'
DBPASS='Ks856985.,'

sudo mysql -u root -pKs856985., <<EOF
CREATE DATABASE $DBNAME;
CREATE USER '$DBUSER'@'localhost' IDENTIFIED BY '$DBPASS';
GRANT ALL PRIVILEGES ON $DBNAME.* TO '$DBUSER'@'localhost';
FLUSH PRIVILEGES;
EOF

# PrestaShop'u indirin
cd /tmp
wget https://download.prestashop.com/download/releases/prestashop_1.7.8.7.zip -O prestashop.zip

# PrestaShop'u açın
sudo apt install unzip -y
sudo unzip prestashop.zip -d /var/www/market.kubilaysen.com/public_html

# Yetkileri ayarlayın
sudo chown -R www-data:www-data /var/www/market.kubilaysen.com/public_html
sudo find /var/www/market.kubilaysen.com/public_html -type d -exec chmod 755 {} \;
sudo find /var/www/market.kubilaysen.com/public_html -type f -exec chmod 644 {} \;

# Güvenlik duvarı ayarları (UFW kullanılıyorsa)
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# SSL sertifikalarını kurun (Let's Encrypt kullanarak)
sudo apt install certbot python3-certbot-apache -y
sudo certbot --apache -d www.kubilaysen.com -d casaos.kubilaysen.com -d market.kubilaysen.com --redirect --non-interactive --agree-tos -m your-email@example.com

# Kurulum tamamlandı mesajı
echo "Kurulum tamamlandı. Lütfen PrestaShop kurulumunu tamamlamak için tarayıcınızdan http://market.kubilaysen.com adresine gidin."
