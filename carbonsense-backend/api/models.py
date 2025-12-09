from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
import uuid


class UserManager(BaseUserManager):
    """Custom user manager."""

    def create_user(self, email, name, password=None, **extra_fields):
        """Create and save a user with the given email, name, and password."""
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
        """Create and save a superuser with the given email, name, and password."""
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


class AreaInfo(models.Model):
    """Area information model."""

    id = models.CharField(primary_key=True, max_length=100)
    name = models.CharField(max_length=255)
    latitude = models.FloatField()
    longitude = models.FloatField()
    bounds_lat_min = models.FloatField()
    bounds_lat_max = models.FloatField()
    bounds_lng_min = models.FloatField()
    bounds_lng_max = models.FloatField()

    class Meta:
        db_table = 'area_info'
        verbose_name = 'Area Information'
        verbose_name_plural = 'Area Information'

    def __str__(self):
        return self.name


class EmissionData(models.Model):
    """Emission data model."""

    DATA_TYPE_CHOICES = [
        ('historical', 'Historical'),
        ('forecast', 'Forecast'),
    ]

    id = models.AutoField(primary_key=True)
    area = models.ForeignKey(AreaInfo, on_delete=models.CASCADE, related_name='emissions')
    date = models.DateField()
    transport = models.FloatField(default=0)
    industry = models.FloatField(default=0)
    energy = models.FloatField(default=0)
    waste = models.FloatField(default=0)
    buildings = models.FloatField(default=0)
    total = models.FloatField(default=0)
    data_type = models.CharField(max_length=20, choices=DATA_TYPE_CHOICES, default='historical')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'emission_data'
        ordering = ['-date']
        indexes = [
            models.Index(fields=['area', 'date']),
            models.Index(fields=['date']),
            models.Index(fields=['data_type']),
        ]

    def __str__(self):
        return f"{self.area.name} - {self.date} ({self.data_type})"

    def save(self, *args, **kwargs):
        """Calculate total emissions before saving."""
        self.total = (
            self.transport +
            self.industry +
            self.energy +
            self.waste +
            self.buildings
        )
        super().save(*args, **kwargs)


class LeaderboardEntry(models.Model):
    """Leaderboard entry model."""

    TREND_CHOICES = [
        ('up', 'Up'),
        ('down', 'Down'),
        ('stable', 'Stable'),
    ]

    id = models.AutoField(primary_key=True)
    rank = models.IntegerField()
    area = models.ForeignKey(AreaInfo, on_delete=models.CASCADE)
    emissions = models.FloatField()
    trend = models.CharField(max_length=10, choices=TREND_CHOICES)
    trend_percentage = models.FloatField()
    period_start = models.DateField()
    period_end = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'leaderboard_entries'
        ordering = ['rank']
        indexes = [
            models.Index(fields=['period_start', 'period_end']),
        ]

    def __str__(self):
        return f"#{self.rank} - {self.area.name}"
