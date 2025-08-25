import django.contrib.auth.models
import django.contrib.auth.validators
import django.contrib.postgres.fields
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models

dailActiveUsers_aggregate_table = """
CREATE MATERIALIZED VIEW dailActiveUsers
WITH (timescaledb.continuous) AS 
SELECT 
    time_bucket('1 hour', time) AS bucket,
    product_id, 
    count(DISTINCT client_id) AS active_users
    FROM gameevent
    GROUP BY bucket, product_id;
"""
dailActiveUsers_refresh_policy = """
SELECT add_continuous_aggregate_policy('dailActiveUsers',
    start_offset => INTERVAL '7 days',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '30 seconds');
"""

dailActiveUsers_conditions = """
ALTER MATERIALIZED VIEW dailActiveUsers
SET (timescaledb.materialized_only = false);
"""


class Migration(migrations.Migration):
    initial = False
    atomic = False

    dependencies = [('analytics', '0002_GameEventHourlyCount')]
    
    operations = [
        migrations.RunSQL(dailActiveUsers_aggregate_table, reverse_sql="DROP MATERIALIZED VIEW dailActiveUsers;"),
        migrations.RunSQL(dailActiveUsers_refresh_policy),
        migrations.RunSQL(dailActiveUsers_conditions)

    ]
