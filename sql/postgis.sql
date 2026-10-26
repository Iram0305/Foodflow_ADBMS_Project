CREATE EXTENSION IF NOT EXISTS postgis;

ALTER TABLE restaurant ADD COLUMN IF NOT EXISTS geom geography(Point, 4326);
ALTER TABLE customer ADD COLUMN IF NOT EXISTS geom geography(Point, 4326);
ALTER TABLE delivery_partner ADD COLUMN IF NOT EXISTS geom geography(Point, 4326);

UPDATE restaurant SET geom = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography;
UPDATE customer SET geom = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography;
UPDATE delivery_partner SET geom = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography;

CREATE INDEX IF NOT EXISTS idx_restaurant_geom ON restaurant USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_customer_geom ON customer USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_partner_geom ON delivery_partner USING GIST (geom);
