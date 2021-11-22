# Xpand-Locust
This is a reference implementing of custom [locust](https://locust.io/) client for Xpand/MariaDB performance testing.
It includes (but not limited to):

- MySQL getenv friendly framework
- Simplified locusfile creation
- Load balancer (during connection time) for Xpand
- Ability to redefine functions weights from configuration file  

## Standalone install

If you want to run locust standalone or master - workers inside the same host please follow next steps:

```bash
# First we need to install git 
curl -s -LJO  https://raw.githubusercontent.com/mariadb-corporation/xpand-locust/main/bin/git_setup.sh | bash -s 

# Checkout xpand-locust 
mkdir -p $HOME/tools && cd $HOME/tools && rm -rf xpand-locust && git clone https://github.com/mariadb-corporation/xpand-locust.git
$HOME/tools/xpand-locust/bin/pyenv_setup.sh
# You have to re-login before continue
# Install python
$HOME/tools/xpand-locust/bin/python3_setup.sh
pip install -r $HOME/tools/xpand-locust/requirements.txt
echo 'export XPAND_LOCUST_HOME="$HOME/tools/xpand-locust"' >>~/.bashrc
```

Before running your locustfile please setup PATH and PYTHONPATH as follow:

```bash
export XPAND_LOCUST_HOME=$HOME/tools/xpand-locust
export PYTHONPATH=$XPAND_LOCUST_HOME
export PATH=$XPAND_LOCUST_HOME/bin:$PATH
```

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
    from xpand_locust import custom_timer

    @task(1)
    @custom_timer  # Now I am going to measure time by myself 
    def my_complex_transaction(self):
        self.client.trx_begin()  # Transaction begin 
        # Insert order 
        _ = self.client._execute(
        "insert into orders (product_name, amount) values (%s, %s)",
            (
                next(self.products_iterator),
                10,
            ),
        row = self.client._query ('SELECT LAST_INSERT_ID();')
        # Update last inserted order 
        _ = self.client._execute(
        "update orders set amount = %s where order_no=%s",
            (
                20,
                row[0],
            ),
        self.client.trx_commit()
```

## SSL support

You should be able to pass any of the following keys: 'ca', 'key', 'cert' as shown below.  

```yaml
 ssl:
    ca: sky.pem
```

## Running Xpand-Locust on the single machine

### Running as standalone

Standalone means you will be running both master and workers as a single process. You will be able to utilize only one processor core.

```bash
swarm_runner.py --swarm-config swarm_config.yaml --log-level DEBUG -f examples/locustfile_simple run_standalone --run-time 100 --users 10 --spawn-rate 10 --csv mysql --params params.yaml
```

### Running master and workers on the same machine as separate processes

This time you will be able to utilize multiple cores on the same machine

First you should start workers:

```bash
swarm_runner.py --swarm-config swarm_config.yaml --log-level DEBUG -f examples/locustfile_simple run_workers --num-workers 2 --drivers 127.0.0.1 --master-host=127.0.0.1
```

Secondly, start master:

```bash
swarm_runner.py --swarm-config swarm_config.yaml --log-level DEBUG -f examples/locustfile_simple run_master --run-time 100 --users 10 --spawn-rate 10 --csv mysql --params params.yaml --expected-workers 2
```

## Other features

### Histograms

It is possible to get histogram per task at the end of the workload. This is approximate a histogram as locust [rounds response time](https://github.com/locustio/locust/blob/master/locust/stats.py#L337) in order to sve amount of data sent between worker and master.

In order to enable histograms you need to add a corresponding keyword to the extra master_options to the swarm_config.yaml:
```yaml
locust_master_options:
    extra_options: --headless --csv-full-history --print-stats --reset-stats --histogram # 
```
