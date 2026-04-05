FROM freeradius/freeradius-server:latest-3.2

COPY mods-available/rest /etc/freeradius/mods-available/rest
COPY sites-available/default /etc/freeradius/sites-available/default
COPY clients.d/local.conf /etc/freeradius/clients.d/local.conf

RUN ln -sf /etc/freeradius/mods-available/rest /etc/freeradius/mods-enabled/rest && \
    ln -sf /etc/freeradius/sites-available/default /etc/freeradius/sites-enabled/default && \
    rm -f /etc/freeradius/sites-enabled/inner-tunnel && \
    rm -f /etc/freeradius/mods-enabled/eap && \
    sed -i 's/secret = testing123/secret = testing123\n\trequire_message_authenticator = yes/' /etc/freeradius/clients.conf
