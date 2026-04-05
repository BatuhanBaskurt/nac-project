-- Kullanıcı kimlik bilgileri
CREATE TABLE IF NOT EXISTS radcheck (
    id SERIAL PRIMARY KEY,
    username VARCHAR(64) NOT NULL,
    attribute VARCHAR(64) NOT NULL,
    op CHAR(2) NOT NULL DEFAULT ':=',
    value VARCHAR(253) NOT NULL
);

-- Kullanıcıya dönülecek atribütler
CREATE TABLE IF NOT EXISTS radreply (
    id SERIAL PRIMARY KEY,
    username VARCHAR(64) NOT NULL,
    attribute VARCHAR(64) NOT NULL,
    op CHAR(2) NOT NULL DEFAULT ':=',
    value VARCHAR(253) NOT NULL
);

-- Kullanıcı-grup ilişkileri
CREATE TABLE IF NOT EXISTS radusergroup (
    id SERIAL PRIMARY KEY,
    username VARCHAR(64) NOT NULL,
    groupname VARCHAR(64) NOT NULL,
    priority INTEGER DEFAULT 1
);

-- Grup bazlı atribütler (VLAN vb.)
CREATE TABLE IF NOT EXISTS radgroupreply (
    id SERIAL PRIMARY KEY,
    groupname VARCHAR(64) NOT NULL,
    attribute VARCHAR(64) NOT NULL,
    op CHAR(2) NOT NULL DEFAULT ':=',
    value VARCHAR(253) NOT NULL
);

-- Accounting kayıtları
CREATE TABLE IF NOT EXISTS radacct (
    radacctid BIGSERIAL PRIMARY KEY,
    acctsessionid VARCHAR(64) NOT NULL,
    acctuniqueid VARCHAR(32) NOT NULL,
    username VARCHAR(64) NOT NULL,
    nasipaddress VARCHAR(15) NOT NULL,
    nasportid VARCHAR(15),
    acctstarttime TIMESTAMP WITH TIME ZONE,
    acctstoptime TIMESTAMP WITH TIME ZONE,
    acctsessiontime INTEGER DEFAULT 0,
    acctinputoctets BIGINT DEFAULT 0,
    acctoutputoctets BIGINT DEFAULT 0,
    acctterminatecause VARCHAR(32),
    acctstartdelay INTEGER DEFAULT 0,
    connectinfo_start VARCHAR(50),
    calledstationid VARCHAR(50),
    callingstationid VARCHAR(50),
    acctstatustype VARCHAR(25)
);

-- Test kullanıcıları ekle
-- Şifreler bcrypt ile hash'lenmiş, gerçek şifreler aşağıda:
-- admin:admin123, employee:emp123, guest:guest123
INSERT INTO radcheck (username, attribute, op, value) VALUES
('admin',    'Cleartext-Password', ':=', 'admin123'),
('employee', 'Cleartext-Password', ':=', 'emp123'),
('guest',    'Cleartext-Password', ':=', 'guest123');

INSERT INTO radusergroup (username, groupname) VALUES
('admin',    'admin'),
('employee', 'employee'),
('guest',    'guest');

-- VLAN atamaları
INSERT INTO radgroupreply (groupname, attribute, op, value) VALUES
('admin',    'Tunnel-Type',             ':=', '13'),
('admin',    'Tunnel-Medium-Type',      ':=', '6'),
('admin',    'Tunnel-Private-Group-Id', ':=', '10'),
('employee', 'Tunnel-Type',             ':=', '13'),
('employee', 'Tunnel-Medium-Type',      ':=', '6'),
('employee', 'Tunnel-Private-Group-Id', ':=', '20'),
('guest',    'Tunnel-Type',             ':=', '13'),
('guest',    'Tunnel-Medium-Type',      ':=', '6'),
('guest',    'Tunnel-Private-Group-Id', ':=', '30');
