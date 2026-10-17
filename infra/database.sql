DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'team') THEN
    CREATE ROLE team NOLOGIN;
  END IF;
END
$$;

GRANT ALL ON SCHEMA public TO team;
