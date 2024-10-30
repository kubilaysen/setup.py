#!/bin/bash

# Hata ayıklama modunu etkinleştirin (isteğe bağlı)
set -euo pipefail
IFS=$'\n\t'

# Kullanıcıya bilgi verin
echo "Kurulum başlatılıyor..."

# 1. Sistemi güncelleyin
echo "Sistemi güncelliyor..."
sudo apt update && sudo apt full-upgrade -y

# 2. Paket yöneticisi sorunlarını düzeltin
echo "Paket yöneticisi sorunlarını düzeltiyor..."
sudo apt --fix-broken install -y

# 3. Apache web sunucusunu kurun
echo "Apache web sunucusu kuruluyor..."
sudo apt install apache2 -y

# 4. Gerekli Apache modüllerini etkinleştirin
echo "Apache modülleri etkinleştiriliyor..."
sudo a2enmod rewrite
sudo a2enmod ssl

# 5. PHP ve gerekli uzantıları kurun
echo "PHP ve gerekli uzantılar kuruluyor..."
sudo apt install php libapache2-mod-php php-mysql php-gd php-curl php-xml php-zip php-mbstring php-intl php-soap php-xmlrpc php-json -y

# 6. Paket yöneticisi sorunlarını tekrar kontrol edin
echo "Paket yöneticisi sorunlarını tekrar kontrol ediyor..."
sudo apt --fix-broken install -y

# 7. MySQL sunucusunu kurun
echo "MySQL sunucusu kuruluyor..."
sudo apt install mysql-server -y

# 8. MySQL root şifresini ayarlayın ve güvenliği artırın
echo "MySQL root şifresi ayarlanıyor ve güvenlik artırılıyor..."
MYSQL_ROOT_PASS='Ks856985.,' # Bunu kendi güçlü şifrenizle değiştirin

sudo mysql -e "ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '${MYSQL_ROOT_PASS}';"
sudo mysql -u root -p"${MYSQL_ROOT_PASS}" -e "DELETE FROM mysql.user WHERE User='';"
sudo mysql -u root -p"${MYSQL_ROOT_PASS}" -e "DROP DATABASE IF EXISTS test;"
sudo mysql -u root -p"${MYSQL_ROOT_PASS}" -e "FLUSH PRIVILEGES;"

# 9. PHP ayarlarını düzenleyin
echo "PHP ayarları düzenleniyor..."
PHP_INI_PATH=$(php -i | grep "Loaded Configuration File" | awk '{print $5}')

sudo sed -i 's/memory_limit = .*/memory_limit = 256M/' "${PHP_INI_PATH}"
sudo sed -i 's/max_execution_time = .*/max_execution_time = 300/' "${PHP_INI_PATH}"
sudo sed -i 's/upload_max_filesize = .*/upload_max_filesize = 64M/' "${PHP_INI_PATH}"
sudo sed -i 's/max_input_vars = .*/max_input_vars = 10000/' "${PHP_INI_PATH}"
sudo sed -i 's/;date.timezone =.*/date.timezone = Europe\/Istanbul/' "${PHP_INI_PATH}"

# 10. Web siteleri için dizinler oluşturun
echo "Web siteleri için dizinler oluşturuluyor..."
sudo mkdir -p /var/www/www.kubilaysen.com/public_html
sudo mkdir -p /var/www/casaos.kubilaysen.com/public_html
sudo mkdir -p /var/www/market.kubilaysen.com/public_html

# 11. Yetkileri ayarlayın
echo "Dizin yetkileri ayarlanıyor..."
sudo chown -R www-data:www-data /var/www/*
sudo find /var/www/* -type d -exec sudo chmod 755 {} \;
sudo find /var/www/* -type f -exec sudo chmod 644 {} \;

# 12. Örnek index.html dosyalarını oluşturun
echo "Örnek index.html dosyaları oluşturuluyor..."
echo "<html><head><title>www.kubilaysen.com</title></head><body><h1>www.kubilaysen.com'a Hoş Geldiniz</h1></body></html>" | sudo tee /var/www/www.kubilaysen.com/public_html/index.html > /dev/null

echo "<html><head><title>casaos.kubilaysen.com</title></head><body><h1>casaos.kubilaysen.com'a Hoş Geldiniz</h1></body></html>" | sudo tee /var/www/casaos.kubilaysen.com/public_html/index.html > /dev/null

echo "<html><head><title>market.kubilaysen.com</title></head><body><h1>market.kubilaysen.com'a Hoş Geldiniz</h1></body></html>" | sudo tee /var/www/market.kubilaysen.com/public_html/index.html > /dev/null

# 13. Apache Sanal Hostlarını yapılandırın
echo "Apache sanal hostları yapılandırılıyor..."

# www.kubilaysen.com
sudo tee /etc/apache2/sites-available/www.kubilaysen.com.conf > /dev/null <<EOT
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
sudo tee /etc/apache2/sites-available/casaos.kubilaysen.com.conf > /dev/null <<EOT
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
sudo tee /etc/apache2/sites-available/market.kubilaysen.com.conf > /dev/null <<EOT
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

# 14. Yeni sanal hostları etkinleştirin ve varsayılan siteyi devre dışı bırakın
echo "Yeni sanal hostlar etkinleştiriliyor ve varsayılan site devre dışı bırakılıyor..."
sudo a2ensite www.kubilaysen.com.conf
sudo a2ensite casaos.kubilaysen.com.conf
sudo a2ensite market.kubilaysen.com.conf
sudo a2dissite 000-default.conf

# 15. Apache'yi yeniden başlatın
echo "Apache web sunucusu yeniden başlatılıyor..."
sudo systemctl restart apache2

# 16. PrestaShop için MySQL veritabanı oluşturun
echo "PrestaShop için MySQL veritabanı ve kullanıcı oluşturuluyor..."
DBNAME='prestashop_db'
DBUSER='kubi'
DBPASS='Ks856985.,' # Bunu kendi güçlü şifrenizle değiştirin

sudo mysql -u root -p"${MYSQL_ROOT_PASS}" <<EOF
CREATE DATABASE ${DBNAME};
CREATE USER '${DBUSER}'@'localhost' IDENTIFIED BY '${DBPASS}';
GRANT ALL PRIVILEGES ON ${DBNAME}.* TO '${DBUSER}'@'localhost';
FLUSH PRIVILEGES;
EOF

# 17. PrestaShop'u indirin
echo "PrestaShop indiriliyor..."
cd /tmp
wget https://download.prestashop.com/download/releases/prestashop_1.7.8.7.zip -O prestashop.zip

# 18. PrestaShop'u açın
echo "PrestaShop açılıyor..."
sudo apt install unzip -y
sudo unzip prestashop.zip -d /var/www/market.kubilaysen.com/public_html

# 19. Yetkileri ayarlayın
echo "PrestaShop dizin yetkileri ayarlanıyor..."
sudo chown -R www-data:www-data /var/www/market.kubilaysen.com/public_html
sudo find /var/www/market.kubilaysen.com/public_html -type d -exec sudo chmod 755 {} \;
sudo find /var/www/market.kubilaysen.com/public_html -type f -exec sudo chmod 644 {} \;

# 20. Güvenlik duvarı ayarları (UFW kullanılıyorsa)
echo "Güvenlik duvarı ayarları yapılıyor..."
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable <<< "y"

# 21. SSL sertifikalarını kurun (Let's Encrypt kullanarak)
echo "Let's Encrypt SSL sertifikaları kuruluyor..."
sudo apt install certbot python3-certbot-apache -y
sudo certbot --apache -d www.kubilaysen.com -d casaos.kubilaysen.com -d market.kubilaysen.com --redirect --non-interactive --agree-tos --expand -m your-email@example.com

# 22. Kurulum tamamlandı mesajı
echo "Kurulum tamamlandı. Lütfen PrestaShop kurulumunu tamamlamak için tarayıcınızdan http://market.kubilaysen.com adresine gidin."
