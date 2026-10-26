DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ff_admin') THEN
        CREATE ROLE ff_admin NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ff_restaurant_manager') THEN
        CREATE ROLE ff_restaurant_manager NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ff_delivery_partner') THEN
        CREATE ROLE ff_delivery_partner NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ff_customer') THEN
        CREATE ROLE ff_customer NOLOGIN;
    END IF;
END
$$;

GRANT USAGE ON SCHEMA public TO ff_admin, ff_restaurant_manager, ff_delivery_partner, ff_customer;

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ff_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ff_admin;

GRANT SELECT ON restaurant, customer TO ff_restaurant_manager;
GRANT SELECT, INSERT, UPDATE, DELETE ON menu_item TO ff_restaurant_manager;
GRANT SELECT ON menu_price_history TO ff_restaurant_manager;
GRANT SELECT, UPDATE ON orders TO ff_restaurant_manager;
GRANT SELECT ON order_item, review TO ff_restaurant_manager;
GRANT SELECT, INSERT ON order_status_history TO ff_restaurant_manager;
GRANT USAGE ON SEQUENCE order_status_history_history_id_seq TO ff_restaurant_manager;

GRANT SELECT ON delivery, delivery_partner TO ff_delivery_partner;
GRANT UPDATE (pickup_time, delivered_time) ON delivery TO ff_delivery_partner;
GRANT UPDATE (latitude, longitude, is_available) ON delivery_partner TO ff_delivery_partner;
GRANT SELECT (order_id, restaurant_id, status, order_time) ON orders TO ff_delivery_partner;
GRANT SELECT (restaurant_id, name, address, latitude, longitude) ON restaurant TO ff_delivery_partner;

GRANT SELECT ON restaurant, menu_item TO ff_customer;
GRANT SELECT ON orders, order_item, payment TO ff_customer;
GRANT SELECT, INSERT ON review TO ff_customer;

ALTER TABLE orders ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS customer_own_orders ON orders;
CREATE POLICY customer_own_orders ON orders
    FOR SELECT
    TO ff_customer
    USING (customer_id = NULLIF(current_setting('app.customer_id', TRUE), '')::INT);

DROP POLICY IF EXISTS staff_all_orders ON orders;
CREATE POLICY staff_all_orders ON orders
    FOR ALL
    TO ff_admin, ff_restaurant_manager, ff_delivery_partner
    USING (TRUE)
    WITH CHECK (TRUE);
