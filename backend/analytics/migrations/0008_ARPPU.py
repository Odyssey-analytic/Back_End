import django.contrib.auth.models
import django.contrib.auth.validators
import django.contrib.postgres.fields
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models

aRPPU_aggregate_table = """
CREATE MATERIALIZED VIEW aRPPU
WITH (timescaledb.continuous) AS 
SELECT
    time_bucket('1 hour', time) AS bucket,
    product_id, 
    SUM(amount)::float / COUNT(DISTINCT client_id) AS arppu
    FROM gameevent ge
    JOIN analytics_bussinessevent be 
    ON ge.id = be.game_event
    GROUP BY product_id, bucket;
"""
aRPPU_refresh_policy = """
SELECT add_continuous_aggregate_policy('aRPPU',
    start_offset => INTERVAL '7 days',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '15 minutes');
"""


class Migration(migrations.Migration):
    initial = False
    atomic = False

    dependencies = [('analytics', '0007_TotalRevenuePerCurrency')]
    
    operations = [
        migrations.RunSQL(aRPPU_aggregate_table, reverse_sql="DROP MATERIALIZED VIEW aRPPU;"),
        migrations.RunSQL(aRPPU_refresh_policy)

    ]




