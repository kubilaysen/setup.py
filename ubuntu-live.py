#!/bin/bash

# Hata ayıklama modunu etkinleştirin (isteğe bağlı)
set -euo pipefail
IFS=$'\n\t'

# Kullanıcıdan şifreleri al
echo "Lütfen MySQL root şifresini girin:"
read -s MYSQL_ROOT_PASS
echo "Lütfen PrestaShop veritabanı kullanıcı şifresini girin:"
read -s DBPASS
DBNAME='prestashop_db'
DBUSER='kubi'

# Kullanıcıya bilgi verin
echo "PrestaShop kurulumu başlatılıyor..."

# 1. Gerekli paketlerin yüklü olup olmadığını kontrol edin
echo "Gerekli paketlerin yüklü olup olmadığını kontrol ediliyor..."
REQUIRED_PACKAGES=(apache2 mysql-server php libapache2-mod-php php-mysql php-gd php-curl php-xml php-zip php-mbstring php-intl php-soap php-xmlrpc php-json unzip certbot python3-certbot-apache)
for package in "${REQUIRED_PACKAGES[@]}"; do
    if ! dpkg -l | grep -q "^ii.*$package"; then
        echo "$package yüklü değil, yüklenecek..."
        sudo apt install -y "$package"
    else
        echo "$package zaten yüklü."
    fi
done

# 2. Apache modüllerini etkinleştirin
echo "Apache modülleri etkinleştiriliyor..."
sudo a2enmod rewrite ssl headers env dir mime

# 3. Apache ve MySQL sunucusunu yeniden başlatın
echo "Apache ve MySQL sunucuları yeniden başlatılıyor..."
sudo systemctl restart apache2
sudo systemctl restart mysql

# 4. MySQL root şifresini ayarlayın ve güvenliği artırın
echo "MySQL root şifresi ayarlanıyor ve güvenlik artırılıyor..."
sudo mysql -e "ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '${MYSQL_ROOT_PASS}';"
sudo mysql -u root -p"${MYSQL_ROOT_PASS}" -e "DELETE FROM mysql.user WHERE User='';"
sudo mysql -u root -p"${MYSQL_ROOT_PASS}" -e "DROP DATABASE IF EXISTS test;"
sudo mysql -u root -p"${MYSQL_ROOT_PASS}" -e "FLUSH PRIVILEGES;"

# 5. PrestaShop için MySQL veritabanı oluşturun
echo "PrestaShop için MySQL veritabanı ve kullanıcı oluşturuluyor..."
sudo mysql -u root -p"${MYSQL_ROOT_PASS}" <<EOF
CREATE DATABASE ${DBNAME};
CREATE USER '${DBUSER}'@'localhost' IDENTIFIED BY '${DBPASS}';
GRANT ALL PRIVILEGES ON ${DBNAME}.* TO '${DBUSER}'@'localhost';
FLUSH PRIVILEGES;
EOF

# 6. Web dizinini oluşturun ve gerekli izinleri ayarlayın
echo "PrestaShop için web dizini oluşturuluyor..."
sudo mkdir -p /var/www/market.kubilaysen.com/public_html
sudo chown -R www-data:www-data /var/www/market.kubilaysen.com
sudo chmod -R 755 /var/www/market.kubilaysen.com

# 7. Apache Sanal Host yapılandırmasını oluşturun
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

# 8. Yeni sanal hostu etkinleştir ve varsayılan siteyi devre dışı bırak
echo "Yeni sanal host etkinleştiriliyor..."
sudo a2ensite market.kubilaysen.com.conf
sudo a2dissite 000-default.conf
sudo systemctl reload apache2

# 9. PrestaShop'u indirin
echo "PrestaShop indiriliyor..."
cd /tmp
wget https://download.prestashop.com/download/releases/prestashop_1.7.8.7.zip -O prestashop.zip

# 10. PrestaShop'u açın
echo "PrestaShop açılıyor..."
sudo unzip -q prestashop.zip -d /var/www/market.kubilaysen.com/public_html

# 11. İzinleri ayarlayın
echo "PrestaShop dizin izinleri ayarlanıyor..."
sudo chown -R www-data:www-data /var/www/market.kubilaysen.com/public_html
sudo find /var/www/market.kubilaysen.com/public_html -type d -exec sudo chmod 755 {} \;
sudo find /var/www/market.kubilaysen.com/public_html -type f -exec sudo chmod 644 {} \;

# 12. Güvenlik duvarı ayarları (UFW kullanılıyorsa)
echo "Güvenlik duvarı ayarları yapılıyor..."
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable <<< "y"

# 13. SSL sertifikalarını kurun (Let's Encrypt kullanarak)
echo "Let's Encrypt SSL sertifikaları kuruluyor..."
sudo certbot --apache -d market.kubilaysen.com --redirect --non-interactive --agree-tos --expand -m your-email@example.com

# 14. Kurulum tamamlandı mesajı
echo "Kurulum tamamlandı. Lütfen PrestaShop kurulumunu tamamlamak için tarayıcınızdan http://market.kubilaysen.com adresine gidin."
