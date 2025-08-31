from django.db import models
from users.models import User
from presalesApp.models import Project


class Category(models.Model):
    category_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200, unique=True)
    description = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return self.name


class Module(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Ticket(models.Model):
    STATUS_CHOICES = [
        ('Open', 'Open'),
        ('Assigned', 'Assigned'),
        ('In Progress', 'In Progress'),
        ('Closed', 'Closed'),
    ]

    ticket_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="aitickets")
    title = models.CharField(max_length=255)
    description = models.CharField(max_length=2000, blank=True)
    module = models.ForeignKey(
        Module, on_delete=models.CASCADE, related_name="aitickets")
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="aitickets")
    priority = models.CharField(max_length=10, choices=[(
        'Low', 'Low'), ('Medium', 'Medium'), ('High', 'High')], default="Low")
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="aitickets")
    project_type = models.CharField(max_length=20, choices=[(
        'Service', 'Service'), ('Incident', 'Incident')], default="Service")
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="Assigned")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    solution = models.CharField(
        max_length=100000, null=True, blank=True, default=None)
    escalation_notified = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.title} (ID: {self.ticket_id})"


class Team(models.Model):
    team_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200, unique=True)
    email = models.EmailField(unique=True, null=True, blank=True)
    description = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return self.name


class TicketAssignment(models.Model):
    STATUS_CHOICES = [
        ('Open', 'Open'),
        ('Assigned', 'Assigned'),
        ('In Progress', 'In Progress'),
        ('Closed', 'Closed'),
    ]

    ticket_assignment_id = models.AutoField(primary_key=True)
    ticket = models.ForeignKey(
        Ticket, on_delete=models.CASCADE, related_name="assignments")
    assigned_to = models.ForeignKey(
        Team, on_delete=models.CASCADE, related_name="assignments")
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="Assigned")
    comments = models.CharField(max_length=100000, blank=True)
    assigned_at = models.DateTimeField(auto_now_add=True)
    email_triggered = models.BooleanField(default=False)

    def __str__(self):
        return f"Assignment {self.ticket_assignment_id} for Ticket {self.ticket.ticket_id}"


class Message(models.Model):
    message_id = models.AutoField(primary_key=True)
    ticket = models.ForeignKey(
        Ticket, on_delete=models.CASCADE, related_name="messages")
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="messages")
    content = models.CharField(max_length=200)
    is_ai_response = models.BooleanField(default=False)
    sent_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message {self.message_id} for Ticket {self.ticket.ticket_id}"


class TeamMember(models.Model):
    ROLE_CHOICES = [
        ('Member', 'Member'),
        ('Leader', 'Leader'),
    ]

    team_member_id = models.AutoField(primary_key=True)
    team = models.ForeignKey(
        Team, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="members")
    role = models.CharField(
        max_length=10, choices=ROLE_CHOICES, default="Member")
    added_at = models.DateTimeField(auto_now_add=True)
    email = models.EmailField(unique=True, null=True, blank=True)

    class Meta:
        unique_together = ('team', 'user')

    def __str__(self):
        return f"{self.user.username} in Team {self.team.name} as {self.role}"


class ChatConvo(models.Model):
    id = models.AutoField(primary_key=True)
    chatwindow_id = models.IntegerField()
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="convo")
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="convo")
    user_query = models.TextField()
    response = models.TextField()
    answer = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Chat {self.id} - {self.user.username}"


class Prompt(models.Model):
    name = models.CharField(max_length=255)
    content = models.TextField()
    created_at = models.DateTimeField(
        auto_now_add=True)
    updated_at = models.DateTimeField(
        auto_now=True)

    def __str__(self):
        return self.name


class TrackingRecord(models.Model):
    serial_number = models.CharField(max_length=100, unique=True)
    response_data = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Tracking Record for {self.serial_number}"
