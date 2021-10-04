# Xpand-Locust
This is a reference implementing of custom [locust](https://locust.io/) client for Xpand/MariaDB performance testing.
It includes (but not limited to):

- MySQL getenv friendly framework
- Simplified locusfile creation
- Load balancer (during connection time) for Xpand
- Ability to redefine functions weights from configuration file  

## Quick start

Setup you sample database using sales.sql and update params.yaml accordantly.

If you would like to rely on default transaction management, you very fist example can be as simple as this (make sure you you have `autocommit: True` in params.yaml):

```python
 @task(1)
    def count_by_product(self):
        _ = self.client.query_all(
            "select count(*) from orders where product_name=%s",
            (next(self.products_iterator),),
        )
```

time for your query will be measured and posted in the final stats as:

```bash
Name                                                                              # reqs      # fails  |     Avg     Min     Max  Median  |   req/s failures/s
----------------------------------------------------------------------------------------------------------------------------------------------------------------
 CUSTOM count_by_product                                                               16     0(0.00%)  |      19      15      25      17  |    0.72    0.00
 CUSTOM insert_order                                                                   55     0(0.00%)  |      19      15      33      18  |    2.48    0.00
----------------------------------------------------------------------------------------------------------------------------------------------------------------
 Aggregated                                                                            71     0(0.00%)  |      19      15      33      18  |    3.20    0.00
```

## More complex example

Before run this example make sure you set `autocommit: False` in params.yaml):

```python
@custom_timer  # Now I am going to measure time by myself 
@task(1)
    def my_complex_transaction(self):
        self.trx_begin()  # Transaction begin 
        # Insert order 
        _ = self.client._execute(
        "insert into orders (product_name, amount) values (%s, %s)",
            (
                next(self.products_iterator),
                10,
            ),
        row = self._query ('SELECT LAST_INSERT_ID();')
        # Update last inserted order 
        _ = self.client._execute(
        "update orders set amount = %s where order_no=%s",
            (
                20,
                row[0],
            ),
        self.trx_commit()
```
