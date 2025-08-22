import django.contrib.auth.models
import django.contrib.auth.validators
import django.contrib.postgres.fields
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models

averageMemoryUsage_aggregate_table = """
CREATE MATERIALIZED VIEW averageMemoryUsage
WITH (timescaledb.continuous) AS 
SELECT
    time_bucket('1 hour', time) AS bucket,
    product_id, 
    AVG(memoryUsage) AS average_memory_usage
    FROM gameevent ge
    JOIN qualityevent qe 
    ON ge_id = qe_game_event
    GROUP BY product_id, bucket;
"""
averageMemoryUsage_refresh_policy = """
SELECT add_continuous_aggregate_policy('averageMemoryUsage',
    start_offset => INTERVAL '7 days',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '15 minutes');
"""

averageMemoryUsage_conditions = """
ALTER MATERIALIZED VIEW averageMemoryUsage
SET (timescaledb.materialized_only = false);
"""


class Migration(migrations.Migration):
    initial = False
    atomic = False

    dependencies = [('analytics', '0004_AverageFPS')]
    
    operations = [
        migrations.RunSQL(averageMemoryUsage_aggregate_table, reverse_sql="DROP MATERIALIZED VIEW averageMemoryUsage;"),
        migrations.RunSQL(averageMemoryUsage_refresh_policy),
        migrations.RunSQL(averageMemoryUsage_conditions)

    ]

