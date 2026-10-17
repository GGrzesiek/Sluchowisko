DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'team') THEN
    CREATE ROLE team NOLOGIN;
  END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'readers') THEN
    CREATE ROLE readers NOLOGIN;
  END IF;
END
$$;

GRANT ALL ON SCHEMA public TO team;
GRANT team TO CURRENT_USER;

GRANT USAGE ON SCHEMA public TO readers;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readers;
ALTER DEFAULT PRIVILEGES FOR ROLE team IN SCHEMA public GRANT SELECT ON TABLES TO readers;

REVOKE team FROM :"team_group";
GRANT readers TO :"team_group";

GRANT team TO :"api_user";
