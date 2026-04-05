FROM freeradius/freeradius-server:latest-3.2

# rest modülünü kopyala
COPY mods-available/rest /etc/freeradius/mods-available/rest
COPY sites-available/default /etc/freeradius/sites-available/default
COPY clients.d/local.conf /etc/freeradius/clients.d/local.conf

# symlink'leri oluştur
RUN ln -sf /etc/freeradius/mods-available/rest /etc/freeradius/mods-enabled/rest && \
    ln -sf /etc/freeradius/sites-available/default /etc/freeradius/sites-enabled/default

