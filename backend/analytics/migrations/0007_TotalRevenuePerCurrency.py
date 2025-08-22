import django.contrib.auth.models
import django.contrib.auth.validators
import django.contrib.postgres.fields
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models

totalRevenuePerCurrency_aggregate_table = """
CREATE MATERIALIZED VIEW totalRevenuePerCurrency
WITH (timescaledb.continuous) AS 
SELECT
    time_bucket('1 hour', time) AS bucket,
    product_id,
    currency, 
    SUM(amount) AS total_amount
    FROM gameevent ge
    JOIN BussinessEvent be 
    ON ge_id = be_game_event
    GROUP BY product_id, currency, bucket;
"""
totalRevenuePerCurrency_refresh_policy = """
SELECT add_continuous_aggregate_policy('totalRevenuePerCurrency',
    start_offset => INTERVAL '7 days',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '15 minutes');
"""



class Migration(migrations.Migration):
    initial = False
    atomic = False

    dependencies = [('analytics', '0006_AverageSessionDuration')]
    
    operations = [
        migrations.RunSQL(totalRevenuePerCurrency_aggregate_table, reverse_sql="DROP MATERIALIZED VIEW totalRevenuePerCurrency;"),
        migrations.RunSQL(totalRevenuePerCurrency_refresh_policy)

    ]



