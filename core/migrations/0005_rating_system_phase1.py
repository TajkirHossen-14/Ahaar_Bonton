# Generated manually for rating system phase 1

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0004_volunteerprofile"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="rating",
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddField(
            model_name="rating",
            name="rating_type",
            field=models.CharField(
                choices=[
                    ("ngo_to_donor", "NGO rates Donor"),
                    ("donor_to_volunteer", "Donor rates Volunteer"),
                    ("ngo_to_volunteer", "NGO rates Volunteer"),
                ],
                default="ngo_to_donor",
                max_length=30,
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="rating",
            name="score",
            field=models.IntegerField(
                choices=[(1, "1"), (2, "2"), (3, "3"), (4, "4"), (5, "5")]
            ),
        ),
        migrations.AlterUniqueTogether(
            name="rating",
            unique_together={("rater", "delivery", "rating_type")},
        ),
    ]
