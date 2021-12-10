CREATE USER 'xpand_locust'@'%' IDENTIFIED BY 'mariadb';
grant SUPER ON *.* TO 'xpand_locust'@'%'; 


CREATE DATABASE IF NOT EXISTS demo_sales;
USE demo_sales;

DROP TABLE IF EXISTS orders;

CREATE TABLE orders (
    order_no     bigint(0) unsigned auto_unique,
    product_name  VARCHAR(64)     NOT NULL,
    amount      int(11)     NOT NULL,
    ordr_date TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (order_no)
);
