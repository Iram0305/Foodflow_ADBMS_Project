CREATE OR REPLACE FUNCTION distance_km(lat1 DOUBLE PRECISION, lon1 DOUBLE PRECISION, lat2 DOUBLE PRECISION, lon2 DOUBLE PRECISION)
RETURNS DOUBLE PRECISION
LANGUAGE SQL IMMUTABLE
AS $$
    SELECT 2 * 6371 * ASIN(SQRT(
        POWER(SIN(RADIANS(lat2 - lat1) / 2), 2) +
        COS(RADIANS(lat1)) * COS(RADIANS(lat2)) * POWER(SIN(RADIANS(lon2 - lon1) / 2), 2)
    ));
$$;

CREATE OR REPLACE FUNCTION record_price_change()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.price <> OLD.price THEN
        UPDATE menu_price_history
        SET valid_to = NOW()
        WHERE item_id = NEW.item_id AND valid_to IS NULL;

        INSERT INTO menu_price_history (item_id, price, valid_from, valid_to)
        VALUES (NEW.item_id, NEW.price, NOW(), NULL);
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_price_history ON menu_item;
CREATE TRIGGER trg_price_history
AFTER UPDATE OF price ON menu_item
FOR EACH ROW
EXECUTE FUNCTION record_price_change();

CREATE OR REPLACE FUNCTION refresh_restaurant_rating()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE restaurant
    SET rating = (SELECT ROUND(AVG(stars), 1) FROM review WHERE restaurant_id = NEW.restaurant_id)
    WHERE restaurant_id = NEW.restaurant_id;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_review_rating ON review;
CREATE TRIGGER trg_review_rating
AFTER INSERT ON review
FOR EACH ROW
EXECUTE FUNCTION refresh_restaurant_rating();

CREATE OR REPLACE FUNCTION log_status_change()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.status <> OLD.status THEN
        INSERT INTO order_status_history (order_id, status, changed_at)
        VALUES (NEW.order_id, NEW.status, NOW());
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_status_history ON orders;
CREATE TRIGGER trg_status_history
AFTER UPDATE OF status ON orders
FOR EACH ROW
EXECUTE FUNCTION log_status_change();

CREATE MATERIALIZED VIEW restaurant_stats AS
SELECT r.restaurant_id,
       r.name,
       r.cuisine,
       r.locality,
       COUNT(o.order_id) AS total_orders,
       COALESCE(SUM(o.total_amount) FILTER (WHERE o.status = 'DELIVERED'), 0) AS revenue,
       COALESCE(ROUND(AVG(o.total_amount), 2), 0) AS avg_order_value,
       r.rating
FROM restaurant r
LEFT JOIN orders o ON o.restaurant_id = r.restaurant_id
GROUP BY r.restaurant_id, r.name, r.cuisine, r.locality, r.rating;

CREATE UNIQUE INDEX idx_restaurant_stats_id ON restaurant_stats(restaurant_id);
