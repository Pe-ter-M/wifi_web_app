-- FreeRADIUS PostgreSQL schema
-- This runs automatically on first container startup via docker-entrypoint-initdb.d

/* Accounting table */
CREATE TABLE IF NOT EXISTS radacct (
    RadAcctId       serial PRIMARY KEY,
    AcctSessionId   text,
    UserName        text,
    NASIPAddress    text,
    AcctStartTime   timestamp with time zone,
    AcctStopTime    timestamp with time zone,
    AcctSessionTime integer,
    AcctInputOctets integer,
    AcctOutputOctets integer,
    FramedIPAddress text,
    CallingStationId text
);

CREATE INDEX IF NOT EXISTS radacct_UserName_idx ON radacct (UserName);

/* Auth check items (password, expiration, etc.) */
CREATE TABLE IF NOT EXISTS radcheck (
    id          serial PRIMARY KEY,
    UserName    text NOT NULL,
    Attribute   text NOT NULL,
    op          VARCHAR(2) DEFAULT '==',
    Value       text NOT NULL
);
CREATE INDEX IF NOT EXISTS radcheck_UserName_idx ON radcheck (UserName);

/* User-specific reply attributes */
CREATE TABLE IF NOT EXISTS radreply (
    id          serial PRIMARY KEY,
    UserName    text NOT NULL,
    Attribute   text NOT NULL,
    op          VARCHAR(2) DEFAULT '=',
    Value       text NOT NULL
);
CREATE INDEX IF NOT EXISTS radreply_UserName_idx ON radreply (UserName);

/* User-to-group mapping */
CREATE TABLE IF NOT EXISTS radusergroup (
    id          serial PRIMARY KEY,
    UserName    text NOT NULL,
    GroupName   text NOT NULL,
    priority    integer DEFAULT 0
);
CREATE INDEX IF NOT EXISTS radusergroup_UserName_idx ON radusergroup (UserName);

/* Post-authentication log */
CREATE TABLE IF NOT EXISTS radpostauth (
    id          serial PRIMARY KEY,
    username    text NOT NULL,
    pass        text,
    reply       text,
    authdate    timestamp with time zone DEFAULT now()
);
CREATE INDEX IF NOT EXISTS radpostauth_username_idx ON radpostauth (username);

/* Group-level check attributes */
CREATE TABLE IF NOT EXISTS radgroupcheck (
    id          serial PRIMARY KEY,
    GroupName   text NOT NULL,
    Attribute   text NOT NULL,
    op          VARCHAR(2) DEFAULT '==',
    Value       text NOT NULL
);
CREATE INDEX IF NOT EXISTS radgroupcheck_GroupName_idx ON radgroupcheck (GroupName);

/* Group-level reply attributes */
CREATE TABLE IF NOT EXISTS radgroupreply (
    id          serial PRIMARY KEY,
    GroupName   text NOT NULL,
    Attribute   text NOT NULL,
    op          VARCHAR(2) DEFAULT '=',
    Value       text NOT NULL
);
CREATE INDEX IF NOT EXISTS radgroupreply_GroupName_idx ON radgroupreply (GroupName);

/* NAS / router table */
CREATE TABLE IF NOT EXISTS nas (
    id          serial PRIMARY KEY,
    nasname     text NOT NULL,
    shortname   text,
    type        text DEFAULT 'other',
    ports       integer,
    secret      text NOT NULL,
    server      text,
    community   text,
    description text
);
CREATE INDEX IF NOT EXISTS nas_nasname_idx ON nas (nasname);