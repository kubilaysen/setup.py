#!/bin/bash

# Hata ayıklama modunu etkinleştirin (isteğe bağlı)
set -euo pipefail
IFS=$'\n\t'

# Kullanıcıya bilgi verin
echo "PrestaShop kurulumu başlatılıyor..."

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

# 6. MySQL sunucusunu kurun
echo "MySQL sunucusu kuruluyor..."
sudo apt install mysql-server -y

# 7. MySQL root şifresini ayarlayın ve güvenliği artırın
echo "MySQL root şifresi ayarlanıyor ve güvenlik artırılıyor..."
MYSQL_ROOT_PASS='Ks856985.,' # Bunu kendi güçlü şifrenizle değiştirin

sudo mysql -e "ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '${MYSQL_ROOT_PASS}';"
sudo mysql -u root -p"${MYSQL_ROOT_PASS}" -e "DELETE FROM mysql.user WHERE User='';"
sudo mysql -u root -p"${MYSQL_ROOT_PASS}" -e "DROP DATABASE IF EXISTS test;"
sudo mysql -u root -p"${MYSQL_ROOT_PASS}" -e "FLUSH PRIVILEGES;"

# 8. PrestaShop için MySQL veritabanı oluşturun
echo "PrestaShop için MySQL veritabanı ve kullanıcı oluşturuluyor..."
DBNAME='prestashop_db'
DBUSER='kubi'
DBPASS='Ks856985.,' # Kendi şifrenizle değiştirin

sudo mysql -u root -p"${MYSQL_ROOT_PASS}" <<EOF
CREATE DATABASE ${DBNAME};
CREATE USER '${DBUSER}'@'localhost' IDENTIFIED BY '${DBPASS}';
GRANT ALL PRIVILEGES ON ${DBNAME}.* TO '${DBUSER}'@'localhost';
FLUSH PRIVILEGES;
EOF

# 9. Web dizinini oluşturun ve gerekli izinleri ayarlayın
echo "PrestaShop için web dizini oluşturuluyor..."
sudo mkdir -p /var/www/market.kubilaysen.com/public_html
sudo chown -R www-data:www-data /var/www/market.kubilaysen.com
sudo chmod -R 755 /var/www/market.kubilaysen.com

# 10. Apache Sanal Host yapılandırmasını oluşturun
echo "Apache sanal host yapılandırması oluşturuluyor..."
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

# 11. Yeni sanal hostu etkinleştir ve varsayılan siteyi devre dışı bırak
echo "Yeni sanal host etkinleştiriliyor..."
sudo a2ensite market.kubilaysen.com.conf
sudo a2dissite 000-default.conf
sudo systemctl restart apache2

# 12. PrestaShop'u indirin
echo "PrestaShop indiriliyor..."
cd /tmp
wget https://download.prestashop.com/download/releases/prestashop_1.7.8.7.zip -O prestashop.zip

# 13. PrestaShop'u açın
echo "PrestaShop açılıyor..."
sudo apt install unzip -y
sudo unzip prestashop.zip -d /var/www/market.kubilaysen.com/public_html

# 14. İzinleri ayarlayın
echo "PrestaShop dizin izinleri ayarlanıyor..."
sudo chown -R www-data:www-data /var/www/market.kubilaysen.com/public_html
sudo find /var/www/market.kubilaysen.com/public_html -type d -exec sudo chmod 755 {} \;
sudo find /var/www/market.kubilaysen.com/public_html -type f -exec sudo chmod 644 {} \;

# 15. Güvenlik duvarı ayarları (UFW kullanılıyorsa)
echo "Güvenlik duvarı ayarları yapılıyor..."
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable <<< "y"

# 16. SSL sertifikalarını kurun (Let's Encrypt kullanarak)
echo "Let's Encrypt SSL sertifikaları kuruluyor..."
sudo apt install certbot python3-certbot-apache -y
sudo certbot --apache -d market.kubilaysen.com --redirect --non-interactive --agree-tos --expand -m kubilaysen1@gmail.com

# 17. Kurulum tamamlandı mesajı
echo "Kurulum tamamlandı. Lütfen PrestaShop kurulumunu tamamlamak için tarayıcınızdan http://market.kubilaysen.com adresine gidin."
