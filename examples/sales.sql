# CREATE USER 'xpand_locust'@'%' IDENTIFIED BY 'mariadb';
# grant SUPER ON *.* TO 'xpand_locust'@'%';


CREATE DATABASE IF NOT EXISTS demo_sales;
USE demo_sales;

DROP TABLE IF EXISTS orders;

CREATE TABLE orders (
    order_no     bigint(0) unsigned auto_unique,
    product_name  VARCHAR(64)     NOT NULL,
    amount      int(11)     NOT NULL,
    order_date TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (order_no)
)  SLICES=10;

CREATE INDEX idx_date_product
   ON orders (order_date, product_name);
