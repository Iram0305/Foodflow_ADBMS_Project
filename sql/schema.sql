DROP MATERIALIZED VIEW IF EXISTS restaurant_stats CASCADE;
DROP TABLE IF EXISTS review CASCADE;
DROP TABLE IF EXISTS delivery CASCADE;
DROP TABLE IF EXISTS payment CASCADE;
DROP TABLE IF EXISTS order_status_history CASCADE;
DROP TABLE IF EXISTS order_item CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS delivery_partner CASCADE;
DROP TABLE IF EXISTS menu_price_history CASCADE;
DROP TABLE IF EXISTS menu_item CASCADE;
DROP TABLE IF EXISTS restaurant CASCADE;
DROP TABLE IF EXISTS customer CASCADE;

CREATE TABLE customer (
    customer_id   INT PRIMARY KEY,
    name          VARCHAR(80)  NOT NULL,
    phone         VARCHAR(15)  NOT NULL UNIQUE,
    email         VARCHAR(120) NOT NULL UNIQUE,
    address       VARCHAR(200) NOT NULL,
    locality      VARCHAR(60)  NOT NULL,
    latitude      DECIMAL(9,6) NOT NULL CHECK (latitude BETWEEN -90 AND 90),
    longitude     DECIMAL(9,6) NOT NULL CHECK (longitude BETWEEN -180 AND 180),
    joined_on     DATE NOT NULL,
    CHECK (email LIKE '%@%')
);

CREATE TABLE restaurant (
    restaurant_id INT PRIMARY KEY,
    name          VARCHAR(100) NOT NULL,
    cuisine       VARCHAR(40)  NOT NULL,
    locality      VARCHAR(60)  NOT NULL,
    address       VARCHAR(200) NOT NULL,
    latitude      DECIMAL(9,6) NOT NULL CHECK (latitude BETWEEN -90 AND 90),
    longitude     DECIMAL(9,6) NOT NULL CHECK (longitude BETWEEN -180 AND 180),
    rating        DECIMAL(2,1) NOT NULL DEFAULT 0 CHECK (rating BETWEEN 0 AND 5),
    cost_for_two  INT NOT NULL CHECK (cost_for_two > 0),
    opens_at      TIME NOT NULL,
    closes_at     TIME NOT NULL,
    is_veg        BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (name, locality)
);

CREATE TABLE menu_item (
    item_id       INT PRIMARY KEY,
    restaurant_id INT NOT NULL REFERENCES restaurant(restaurant_id) ON DELETE CASCADE,
    item_name     VARCHAR(100) NOT NULL,
    category      VARCHAR(40)  NOT NULL,
    price         DECIMAL(8,2) NOT NULL CHECK (price > 0),
    stock         INT NOT NULL DEFAULT 0 CHECK (stock >= 0),
    is_veg        BOOLEAN NOT NULL DEFAULT TRUE,
    version       INT NOT NULL DEFAULT 1,
    UNIQUE (restaurant_id, item_name)
);

CREATE TABLE menu_price_history (
    history_id    SERIAL PRIMARY KEY,
    item_id       INT NOT NULL REFERENCES menu_item(item_id) ON DELETE CASCADE,
    price         DECIMAL(8,2) NOT NULL CHECK (price > 0),
    valid_from    TIMESTAMP NOT NULL,
    valid_to      TIMESTAMP,
    CHECK (valid_to IS NULL OR valid_to > valid_from)
);

CREATE TABLE delivery_partner (
    partner_id    INT PRIMARY KEY,
    name          VARCHAR(80) NOT NULL,
    phone         VARCHAR(15) NOT NULL UNIQUE,
    vehicle       VARCHAR(20) NOT NULL CHECK (vehicle IN ('BIKE', 'SCOOTER', 'BICYCLE', 'EV_BIKE')),
    latitude      DECIMAL(9,6) NOT NULL,
    longitude     DECIMAL(9,6) NOT NULL,
    is_available  BOOLEAN NOT NULL DEFAULT TRUE,
    rating        DECIMAL(2,1) NOT NULL DEFAULT 4.0 CHECK (rating BETWEEN 0 AND 5),
    joined_on     DATE NOT NULL
);

CREATE TABLE orders (
    order_id      SERIAL PRIMARY KEY,
    customer_id   INT NOT NULL REFERENCES customer(customer_id),
    restaurant_id INT NOT NULL REFERENCES restaurant(restaurant_id),
    order_time    TIMESTAMP NOT NULL,
    status        VARCHAR(20) NOT NULL CHECK (status IN ('PLACED', 'ACCEPTED', 'PREPARING', 'PICKED_UP', 'DELIVERED', 'CANCELLED')),
    total_amount  DECIMAL(10,2) NOT NULL CHECK (total_amount >= 0)
);

CREATE TABLE order_item (
    order_id      INT NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
    item_id       INT NOT NULL REFERENCES menu_item(item_id),
    quantity      INT NOT NULL CHECK (quantity > 0),
    unit_price    DECIMAL(8,2) NOT NULL CHECK (unit_price > 0),
    PRIMARY KEY (order_id, item_id)
);

CREATE TABLE order_status_history (
    history_id    SERIAL PRIMARY KEY,
    order_id      INT NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
    status        VARCHAR(20) NOT NULL CHECK (status IN ('PLACED', 'ACCEPTED', 'PREPARING', 'PICKED_UP', 'DELIVERED', 'CANCELLED')),
    changed_at    TIMESTAMP NOT NULL
);

CREATE TABLE payment (
    payment_id    SERIAL PRIMARY KEY,
    order_id      INT NOT NULL UNIQUE REFERENCES orders(order_id) ON DELETE CASCADE,
    amount        DECIMAL(10,2) NOT NULL CHECK (amount >= 0),
    method        VARCHAR(20) NOT NULL CHECK (method IN ('UPI', 'CARD', 'WALLET', 'CASH', 'NETBANKING')),
    status        VARCHAR(20) NOT NULL CHECK (status IN ('SUCCESS', 'FAILED', 'REFUNDED', 'PENDING')),
    paid_at       TIMESTAMP NOT NULL
);

CREATE TABLE delivery (
    order_id       INT PRIMARY KEY REFERENCES orders(order_id) ON DELETE CASCADE,
    partner_id     INT NOT NULL REFERENCES delivery_partner(partner_id),
    pickup_time    TIMESTAMP,
    delivered_time TIMESTAMP,
    distance_km    DECIMAL(5,2) NOT NULL CHECK (distance_km >= 0),
    CHECK (delivered_time IS NULL OR pickup_time IS NULL OR delivered_time >= pickup_time)
);

CREATE TABLE review (
    review_id     SERIAL PRIMARY KEY,
    order_id      INT NOT NULL UNIQUE REFERENCES orders(order_id) ON DELETE CASCADE,
    customer_id   INT NOT NULL REFERENCES customer(customer_id),
    restaurant_id INT NOT NULL REFERENCES restaurant(restaurant_id),
    stars         INT NOT NULL CHECK (stars BETWEEN 1 AND 5),
    comment       VARCHAR(300),
    reviewed_at   TIMESTAMP NOT NULL
);
