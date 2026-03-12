from django.contrib.gis.db import models

class FuelStation(models.Model):
    opis_id = models.IntegerField(unique=True)
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=2)
    rack_id = models.IntegerField()
    retail_price = models.DecimalField(max_digits=10, decimal_places=3)
    location = models.PointField(srid=4326, blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.city}, {self.state}) - ${self.retail_price}"
