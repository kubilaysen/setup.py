#!/bin/bash

# Hata ayıklama modunu etkinleştirin
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
echo "Apache ve PrestaShop kurulumları başlatılıyor..."

# 1. Apache’yi kaldır ve temizle
echo "Apache’yi kaldırıyor ve temizliyor..."
sudo systemctl stop apache2 || true
sudo apt remove --purge -y apache2 apache2-utils apache2-bin apache2.2-common
sudo apt autoremove -y
sudo rm -rf /etc/apache2 /var/www/html /var/log/apache2 /var/www/*

# 2. Apache’yi yeniden kur
echo "Apache’yi yeniden kuruyor..."
sudo apt update
sudo apt install -y apache2

# 3. ServerName ayarla
echo "Apache ServerName ayarlanıyor..."
echo "ServerName localhost" | sudo tee /etc/apache2/conf-available/servername.conf
sudo a2enconf servername

# 4. Gerekli Apache modüllerini etkinleştir
echo "Apache modülleri etkinleştiriliyor..."
sudo a2enmod rewrite ssl headers env dir mime

# 5. Apache yapılandırma dosyasını test edin
echo "Apache yapılandırması test ediliyor..."
if ! sudo apache2ctl configtest; then
    echo "Apache yapılandırma testinde hata bulundu. Lütfen yapılandırma dosyalarını kontrol edin."
    exit 1
fi

# 6. Apache’yi yeniden başlatın
echo "Apache sunucusu yeniden başlatılıyor..."
sudo systemctl restart apache2

# 7. Gerekli diğer paketleri kur
echo "Gerekli diğer paketler kuruluyor..."
sudo apt install -y mysql-server php libapache2-mod-php php-mysql php-gd php-curl php-xml php-zip php-mbstring php-intl php-soap php-xmlrpc php-json unzip certbot python3-certbot-apache

# 8. MySQL root şifresini ayarla ve güvenliği artır
echo "MySQL root şifresi ayarlanıyor ve güvenlik artırılıyor..."
sudo mysql -e "ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '${MYSQL_ROOT_PASS}';"
sudo mysql -u root -p"${MYSQL_ROOT_PASS}" -e "DELETE FROM mysql.user WHERE User='';"
sudo mysql -u root -p"${MYSQL_ROOT_PASS}" -e "DROP DATABASE IF EXISTS test;"
sudo mysql -u root -p"${MYSQL_ROOT_PASS}" -e "FLUSH PRIVILEGES;"

# 9. PrestaShop için MySQL veritabanı oluştur
echo "PrestaShop için MySQL veritabanı ve kullanıcı oluşturuluyor..."
sudo mysql -u root -p"${MYSQL_ROOT_PASS}" <<EOF
CREATE DATABASE ${DBNAME};
CREATE USER '${DBUSER}'@'localhost' IDENTIFIED BY '${DBPASS}';
GRANT ALL PRIVILEGES ON ${DBNAME}.* TO '${DBUSER}'@'localhost';
FLUSH PRIVILEGES;
EOF

# 10. PrestaShop için web dizinini oluştur ve izinleri ayarla
echo "PrestaShop için web dizini oluşturuluyor..."
sudo mkdir -p /var/www/market.kubilaysen.com/public_html
sudo chown -R www-data:www-data /var/www/market.kubilaysen.com
sudo chmod -R 755 /var/www/market.kubilaysen.com

# 11. Apache sanal host yapılandırmasını oluştur
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

# 12. Yeni sanal hostu etkinleştir ve varsayılan siteyi devre dışı bırak
echo "Yeni sanal host etkinleştiriliyor..."
sudo a2ensite market.kubilaysen.com.conf
sudo a2dissite 000-default.conf

# 13. Apache yapılandırmasını tekrar test edin ve yeniden başlatın
echo "Apache yapılandırması tekrar test ediliyor..."
if sudo apache2ctl configtest; then
    sudo systemctl reload apache2 || { echo "Apache yeniden yüklenemedi."; exit 1; }
    echo "Apache yapılandırması başarılı bir şekilde yeniden yüklendi."
else
    echo "Yapılandırma hatası bulundu, Apache yeniden başlatılmadı. Kontrol edin."
    exit 1
fi

# 14. PrestaShop 8.0'u indirin
echo "PrestaShop 8.0 indiriliyor..."
cd /tmp
wget https://download.prestashop.com/download/releases/prestashop_8.0.0.zip -O prestashop.zip

# 15. PrestaShop’u web dizinine açın
echo "PrestaShop açılıyor..."
sudo unzip -q prestashop.zip -d /var/www/market.kubilaysen.com/public_html

# 16. İzinleri ayarlayın
echo "PrestaShop dizin izinleri ayarlanıyor..."
sudo chown -R www-data:www-data /var/www/market.kubilaysen.com/public_html
sudo find /var/www/market.kubilaysen.com/public_html -type d -exec sudo chmod 755 {} \;
sudo find /var/www/market.kubilaysen.com/public_html -type f -exec sudo chmod 644 {} \;

# 17. Güvenlik duvarı ayarları (UFW kullanılıyorsa)
echo "Güvenlik duvarı ayarları yapılıyor..."
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable <<< "y"

# 18. SSL sertifikalarını kur (Let's Encrypt kullanarak)
echo "Let's Encrypt SSL sertifikaları kuruluyor..."
sudo certbot --apache -d market.kubilaysen.com --redirect --non-interactive --agree-tos --expand -m your-email@example.com

# 19. Kurulum tamamlandı mesajı
echo "Kurulum tamamlandı. Lütfen PrestaShop kurulumunu tamamlamak için tarayıcınızdan http://market.kubilaysen.com adresine gidin."
