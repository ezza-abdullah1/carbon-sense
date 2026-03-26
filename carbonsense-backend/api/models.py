from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
import uuid


class UserManager(BaseUserManager):
    """Custom user manager."""

    def create_user(self, email, name, password=None, **extra_fields):
        if not email:
            raise ValueError('Users must have an email address')
        if not name:
            raise ValueError('Users must have a name')

        email = self.normalize_email(email)
        user = self.model(email=email, name=name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, name, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, name, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Custom user model."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, max_length=255)
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    class Meta:
        db_table = 'users'
        ordering = ['-date_joined']

    def __str__(self):
        return self.email


# ============================================================================
# Unmanaged models — map to existing Supabase tables (read-only from Django)
# ============================================================================

def make_area_id(source_name, sector='energy'):
    """Generate a consistent area ID slug from a location source name."""
    return f"{source_name.lower().replace(' ', '_')}_{sector}"


class ForecastRun(models.Model):
    pipeline = models.TextField()
    generated_at = models.DateTimeField()
    data_source = models.TextField()
    sector = models.CharField(max_length=100)
    region = models.TextField()
    historical_start = models.DateField()
    historical_end = models.DateField()
    forecast_horizon_months = models.IntegerField()
    forecast_start = models.DateField()
    forecast_end = models.DateField()
    model_architecture = models.CharField(max_length=100)
    is_active = models.BooleanField()

    class Meta:
        managed = False
        db_table = 'forecast_runs'


class Location(models.Model):
    forecast_run = models.ForeignKey(ForecastRun, on_delete=models.DO_NOTHING,
                                     related_name='locations')
    source = models.TextField()
    type = models.TextField()
    latitude = models.FloatField()
    longitude = models.FloatField()
    uc_code = models.TextField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'locations'


class EmissionPoint(models.Model):
    location = models.ForeignKey(Location, on_delete=models.DO_NOTHING,
                                  related_name='emission_points')
    date = models.DateField()
    month_label = models.TextField()
    emissions = models.FloatField()
    point_type = models.CharField(max_length=20)
    temperature = models.FloatField(null=True)
    cdd = models.FloatField(null=True)
    humidity = models.FloatField(null=True)
    lower_ci = models.FloatField(null=True)
    upper_ci = models.FloatField(null=True)
    confidence = models.CharField(max_length=20, null=True)

    class Meta:
        managed = False
        db_table = 'emission_points'


class LocationModelInfo(models.Model):
    location = models.OneToOneField(Location, on_delete=models.DO_NOTHING,
                                     primary_key=True)
    architecture = models.CharField(max_length=100)
    test_mape = models.FloatField(null=True)
    test_r2 = models.FloatField(null=True)

    class Meta:
        managed = False
        db_table = 'location_model_info'


class LocationSummary(models.Model):
    location = models.OneToOneField(Location, on_delete=models.DO_NOTHING,
                                     primary_key=True)
    last_historical_date = models.CharField(max_length=50)
    last_historical_emissions = models.FloatField()
    forecast_12m_last = models.FloatField()
    forecast_12m_average = models.FloatField()
    forecast_12m_total = models.FloatField()
    change_pct = models.FloatField()
    change_tonnes = models.FloatField()
    trend = models.CharField(max_length=20)
    total_historical_tonnes = models.FloatField()
    sub_sector_data = models.JSONField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'location_summaries'


class AggregateForecastPoint(models.Model):
    forecast_run = models.ForeignKey(ForecastRun, on_delete=models.DO_NOTHING,
                                      related_name='aggregate_points')
    date = models.DateField()
    value = models.FloatField()
    lower_bound = models.FloatField()
    upper_bound = models.FloatField()
    temperature = models.FloatField(null=True)
    cdd = models.FloatField(null=True)
    humidity = models.FloatField(null=True)

    class Meta:
        managed = False
        db_table = 'aggregate_forecast_points'
