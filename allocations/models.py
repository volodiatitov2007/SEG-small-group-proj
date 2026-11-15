from django.contrib.auth.models import AbstractUser
from django.db import models



class User(AbstractUser):
    """A user of the group allocation application.

    AbstractUser already provides username, first_name, last_name, email,
    password and is_superuser (amongst others). We redefine first_name,
    last_name and email so that they are required, and so that no two users
    can share an email address.
    """

    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField(unique=True)

    class Meta:
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f'{self.get_full_name()} ({self.username})'


class Project(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='projects')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Cohort(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='cohorts')
    original_filename = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    columns = models.JSONField(default=list)

    def __str__(self):
        return self.original_filename


class Student(models.Model):
    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE, related_name='students')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    gender = models.PositiveSmallIntegerField(null=True, blank=True)
    ethnicity = models.PositiveSmallIntegerField(null=True, blank=True)
    c_score = models.PositiveSmallIntegerField(null=True, blank=True)
    extra = models.JSONField(default=dict)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['cohort', 'email'], name='unique_email_per_cohort')]
        ordering = ['last_name', 'first_name', 'email']

    def __str__(self):
        return f'{self.first_name} {self.last_name}'


class AllocationRun(models.Model):
    class Status(models.TextChoices):
        OK = 'ok', 'Allocated'
        INFEASIBLE = 'infeasible', 'Known infeasible'
        TIMEOUT = 'timeout', 'None found in time'

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='runs')
    cohort = models.ForeignKey(Cohort, on_delete=models.PROTECT, related_name='runs')
    policy_snapshot = models.JSONField(default=dict)
    status = models.CharField(max_length=12, choices=Status.choices)
    message = models.TextField(blank=True)
    violations = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    duration_seconds = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f'{self.project}: run {self.pk}'


class Team(models.Model):
    run = models.ForeignKey(AllocationRun, on_delete=models.CASCADE, related_name='teams')
    name = models.CharField(max_length=50)

    class Meta:
        ordering = ['name', 'pk']

    def __str__(self):
        return self.name


class TeamMembership(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='members')
    student = models.ForeignKey(Student, on_delete=models.PROTECT, related_name='team_memberships')

    class Meta:
        constraints = [models.UniqueConstraint(fields=['team', 'student'], name='unique_member')]
