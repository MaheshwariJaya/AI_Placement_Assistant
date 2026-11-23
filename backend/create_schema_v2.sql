-- ==============================================================================
-- Schema Isolation Setup for AI-Powered Placement Intelligence System
-- Target Database: placement_intelligence_local
-- ==============================================================================

CREATE SCHEMA placement_app_v2 AUTHORIZATION placement_app;

GRANT ALL ON SCHEMA placement_app_v2 TO placement_app;

ALTER DEFAULT PRIVILEGES FOR ROLE placement_app
IN SCHEMA placement_app_v2
GRANT ALL ON TABLES TO placement_app;

ALTER DEFAULT PRIVILEGES FOR ROLE placement_app
IN SCHEMA placement_app_v2
GRANT ALL ON SEQUENCES TO placement_app;

ALTER DEFAULT PRIVILEGES FOR ROLE placement_app
IN SCHEMA placement_app_v2
GRANT ALL ON ROUTINES TO placement_app;

