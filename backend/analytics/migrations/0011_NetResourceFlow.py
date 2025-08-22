import django.contrib.auth.models
import django.contrib.auth.validators
import django.contrib.postgres.fields
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models

netResourceFlow_aggregate_table = """
CREATE MATERIALIZED VIEW netResourceFlow
WITH (timescaledb.continuous) AS 
SELECT
    time_bucket('1 hour', time) AS bucket,
    product_id,
    re."itemType", 
    SUM(CASE WHEN re."flowType" = 'Source' THEN amount ELSE -amount END) AS net_flow
    FROM gameevent ge
    JOIN analytics_resourceevent re 
    ON ge.id = re.game_event
    GROUP BY product_id, bucket, re."itemType";
"""
netResourceFlow_refresh_policy = """
SELECT add_continuous_aggregate_policy('netResourceFlow',
    start_offset => INTERVAL '7 days',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '15 minutes');
"""


class Migration(migrations.Migration):
    initial = False
    atomic = False

    dependencies = [('analytics', '0010_AverageTriesPerLevel')]
    
    operations = [
        migrations.RunSQL(netResourceFlow_aggregate_table, reverse_sql="DROP MATERIALIZED VIEW netResourceFlow;"),
        migrations.RunSQL(netResourceFlow_refresh_policy)

    ]




