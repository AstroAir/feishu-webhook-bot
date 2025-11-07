# Automation Guide

This guide explains how to use the Automation Engine to create declarative workflows without writing Python code.

## Overview

The Automation Engine allows you to define workflows that:

- Run on schedules (cron expressions)
- React to Feishu webhook events
- Execute multi-step actions (HTTP requests, send messages, render templates)
- Use message templates with variable substitution
- Chain actions together with context passing

## Quick Start

### Basic Schedule-based Automation

```yaml
automations:
  - name: "morning-greeting"
    description: "Send greeting every weekday at 9 AM"
    enabled: true
    trigger:
      type: "schedule"
      schedule:
        mode: "cron"
        arguments:
          day_of_week: "mon-fri"
          hour: "9"
          minute: "0"
    default_webhooks: ["default"]
    actions:
      - type: "send_text"
        text: "Good morning! Have a productive day!"
```

## Triggers

### Schedule Trigger

Run automation on a schedule using cron expressions:

```yaml
trigger:
  type: "schedule"
  schedule:
    mode: "cron"
    arguments:
      hour: "9"
      minute: "0"
      day_of_week: "mon-fri"
```

**Common cron arguments:**

- `year` - Year (e.g., "2024")
- `month` - Month (1-12)
- `day` - Day of month (1-31)
- `week` - Week of year (1-53)
- `day_of_week` - Day of week (0-6, 0=Monday, or "mon-fri")
- `hour` - Hour (0-23)
- `minute` - Minute (0-59)
- `second` - Second (0-59)

### Event Trigger

React to Feishu webhook events:

```yaml
trigger:
  type: "event"
  event:
    event_type: "im.message.receive_v1"
    conditions:
      - path: "event.message.content"
        operator: "contains"
        value: "alert"
```

**Supported operators:**

- `equals` - Exact match
- `contains` - Substring match
- `starts_with` - Prefix match
- `ends_with` - Suffix match
- `regex` - Regular expression match
- `gt` - Greater than (numeric)
- `lt` - Less than (numeric)
- `gte` - Greater than or equal
- `lte` - Less than or equal

## Actions

### Send Text

Send a plain text message:

```yaml
actions:
  - type: "send_text"
    text: "Hello, Feishu!"
    webhooks: ["default"]  # Optional: override default webhooks
```

### Send Template

Render and send a message template:

```yaml
actions:
  - type: "send_template"
    template: "daily_report"
    context:
      date: "${event_date}"
      status: "operational"
    webhooks: ["default"]
```

### HTTP Request

Make an HTTP request and save response:

```yaml
actions:
  - type: "http_request"
    request:
      method: "GET"
      url: "https://api.example.com/stats"
      headers:
        Authorization: "Bearer ${API_TOKEN}"
      save_as: "stats"
```

The response is saved in context and can be used in subsequent actions:

```yaml
actions:
  - type: "http_request"
    request:
      method: "GET"
      url: "https://api.example.com/stats"
      save_as: "stats"
  
  - type: "send_text"
    text: "Total users: ${stats.total_users}"
```

## Templates

Define reusable message templates:

```yaml
templates:
  - name: "daily_report"
    description: "Daily report card"
    type: "card"
    engine: "string"  # or "format"
    content: |
      {
        "header": {
          "template": "blue",
          "title": {"tag": "plain_text", "content": "Daily Report"}
        },
        "elements": [
          {
            "tag": "markdown",
            "content": "**Date:** ${date}\n**Status:** ${status}"
          }
        ]
      }
```

### Template Engines

- `string` - Python string.Template (uses `${variable}`)
- `format` - Python str.format (uses `{variable}`)

## Context Variables

Automations have access to context variables:

- `${event_date}` - Current date
- `${event_time}` - Current time
- `${event_timestamp}` - Current timestamp
- `${event.*}` - Event payload fields (for event-triggered automations)
- `${<action_save_as>.*}` - Results from previous HTTP requests

## Examples

### Example 1: Daily Status Report

```yaml
templates:
  - name: "status_report"
    type: "card"
    content: |
      {
        "header": {"template": "blue", "title": {"tag": "plain_text", "content": "Status Report"}},
        "elements": [{"tag": "markdown", "content": "${report}"}]
      }

automations:
  - name: "daily-status"
    trigger:
      type: "schedule"
      schedule:
        mode: "cron"
        arguments: { hour: "18", minute: "0" }
    actions:
      - type: "http_request"
        request:
          method: "GET"
          url: "https://api.example.com/status"
          save_as: "status"
      
      - type: "send_template"
        template: "status_report"
        context:
          report: "System status: ${status.health}"
```

### Example 2: Alert on Message

```yaml
automations:
  - name: "urgent-alert"
    trigger:
      type: "event"
      event:
        event_type: "im.message.receive_v1"
        conditions:
          - path: "event.message.content"
            operator: "contains"
            value: "URGENT"
    actions:
      - type: "send_text"
        text: "🚨 URGENT message received!"
```

### Example 3: Multi-step Workflow

```yaml
automations:
  - name: "fetch-and-notify"
    trigger:
      type: "schedule"
      schedule:
        mode: "cron"
        arguments: { hour: "12", minute: "0" }
    actions:
      # Step 1: Fetch data
      - type: "http_request"
        request:
          method: "GET"
          url: "https://api.example.com/metrics"
          save_as: "metrics"
      
      # Step 2: Fetch additional data
      - type: "http_request"
        request:
          method: "GET"
          url: "https://api.example.com/alerts"
          save_as: "alerts"
      
      # Step 3: Send combined report
      - type: "send_text"
        text: |
          Metrics: ${metrics.count}
          Alerts: ${alerts.count}
```

## Real-World Examples

### Monitoring & Alerting

#### Example 4: Server Health Check with Alerting

Monitor server health and send alerts if status is degraded:

```yaml
templates:
  - name: "health_alert"
    type: "card"
    content: |
      {
        "header": {"template": "red", "title": {"tag": "plain_text", "content": "⚠️ Health Alert"}},
        "elements": [
          {
            "tag": "markdown",
            "content": "**Server:** ${server}\n**Status:** ${status}\n**CPU:** ${cpu}%\n**Memory:** ${memory}%\n**Uptime:** ${uptime}h"
          },
          {"tag": "action", "actions": [{"type": "button", "text": "View Dashboard", "url": "https://dashboard.example.com"}]}
        ]
      }

automations:
  - name: "server-health-check"
    description: "Check server health every 5 minutes and alert if degraded"
    enabled: true
    trigger:
      type: "schedule"
      schedule:
        mode: "cron"
        arguments:
          minute: "*/5"  # Every 5 minutes
    default_webhooks: ["alerts"]
    actions:
      # Fetch server metrics
      - type: "http_request"
        request:
          method: "GET"
          url: "https://api.example.com/servers/prod-01/health"
          headers:
            Authorization: "Bearer ${HEALTH_API_TOKEN}"
          timeout: 5
          save_as: "health"

      # Send alert if status is not healthy
      - type: "send_template"
        template: "health_alert"
        context:
          server: "prod-01"
          status: "${health.status}"
          cpu: "${health.cpu_usage}"
          memory: "${health.memory_usage}"
          uptime: "${health.uptime_hours}"
        webhooks: ["alerts"]
```

**Key Features:**

- Runs every 5 minutes using `minute: "*/5"`
- Fetches real-time server metrics
- Uses environment variable for API token
- Sends formatted alert card with dashboard link
- Can be easily adapted for multiple servers

#### Example 5: API Endpoint Monitoring

Monitor multiple API endpoints and report status:

```yaml
templates:
  - name: "api_status_report"
    type: "card"
    content: |
      {
        "header": {"template": "blue", "title": {"tag": "plain_text", "content": "API Status Report"}},
        "elements": [
          {"tag": "markdown", "content": "**Timestamp:** ${timestamp}\n\n${status_list}"},
          {"tag": "note", "content": "Last updated: ${event_time}"}
        ]
      }

automations:
  - name: "api-endpoint-monitor"
    description: "Monitor API endpoints every 10 minutes"
    enabled: true
    trigger:
      type: "schedule"
      schedule:
        mode: "cron"
        arguments:
          minute: "*/10"
    default_webhooks: ["monitoring"]
    actions:
      # Check API endpoint 1
      - type: "http_request"
        request:
          method: "GET"
          url: "https://api.example.com/health"
          timeout: 3
          save_as: "api1"

      # Check API endpoint 2
      - type: "http_request"
        request:
          method: "GET"
          url: "https://api2.example.com/health"
          timeout: 3
          save_as: "api2"

      # Check API endpoint 3
      - type: "http_request"
        request:
          method: "GET"
          url: "https://api3.example.com/health"
          timeout: 3
          save_as: "api3"

      # Send combined status report
      - type: "send_template"
        template: "api_status_report"
        context:
          timestamp: "${event_timestamp}"
          status_list: |
            🟢 API 1: ${api1.status}
            🟢 API 2: ${api2.status}
            🟢 API 3: ${api3.status}
```

**Key Features:**

- Chains multiple HTTP requests
- Uses context variables from previous requests
- Combines results into single report
- Short timeout (3s) to detect slow endpoints
- Easy to add more endpoints

### Data Aggregation & Reporting

#### Example 6: Daily Metrics Aggregation

Collect metrics from multiple sources and generate daily report:

```yaml
templates:
  - name: "daily_metrics"
    type: "card"
    content: |
      {
        "header": {"template": "blue", "title": {"tag": "plain_text", "content": "📊 Daily Metrics Report"}},
        "elements": [
          {"tag": "markdown", "content": "**Date:** ${date}\n\n**Traffic:**\n- Page Views: ${traffic.page_views}\n- Unique Users: ${traffic.unique_users}\n- Bounce Rate: ${traffic.bounce_rate}%\n\n**Performance:**\n- Avg Response Time: ${perf.avg_response_ms}ms\n- Error Rate: ${perf.error_rate}%\n- Uptime: ${perf.uptime}%\n\n**Conversions:**\n- Total: ${conversions.total}\n- Rate: ${conversions.rate}%\n- Revenue: $${conversions.revenue}"}
        ]
      }

automations:
  - name: "daily-metrics-report"
    description: "Generate daily metrics report at 8 AM"
    enabled: true
    trigger:
      type: "schedule"
      schedule:
        mode: "cron"
        arguments:
          hour: "8"
          minute: "0"
          day_of_week: "mon-fri"
    default_webhooks: ["reports"]
    actions:
      # Fetch traffic metrics
      - type: "http_request"
        request:
          method: "GET"
          url: "https://analytics.example.com/api/traffic?date=${event_date}"
          headers:
            Authorization: "Bearer ${ANALYTICS_TOKEN}"
          save_as: "traffic"

      # Fetch performance metrics
      - type: "http_request"
        request:
          method: "GET"
          url: "https://monitoring.example.com/api/performance?date=${event_date}"
          headers:
            Authorization: "Bearer ${MONITORING_TOKEN}"
          save_as: "perf"

      # Fetch conversion metrics
      - type: "http_request"
        request:
          method: "GET"
          url: "https://crm.example.com/api/conversions?date=${event_date}"
          headers:
            Authorization: "Bearer ${CRM_TOKEN}"
          save_as: "conversions"

      # Send aggregated report
      - type: "send_template"
        template: "daily_metrics"
        context:
          date: "${event_date}"
          traffic: "${traffic}"
          perf: "${perf}"
          conversions: "${conversions}"
```

**Key Features:**

- Aggregates data from 3 different sources
- Runs only on weekdays (mon-fri)
- Uses date parameter in API calls
- Combines all metrics into single card
- Easy to add more data sources

#### Example 7: Weekly Team Summary

Generate weekly summary of team activities:

```yaml
templates:
  - name: "weekly_summary"
    type: "card"
    content: |
      {
        "header": {"template": "blue", "title": {"tag": "plain_text", "content": "📋 Weekly Team Summary"}},
        "elements": [
          {"tag": "markdown", "content": "**Week of:** ${week_start}\n\n**Completed Tasks:** ${tasks.completed}\n**In Progress:** ${tasks.in_progress}\n**Blocked:** ${tasks.blocked}\n\n**Team Metrics:**\n- Avg Response Time: ${metrics.avg_response}h\n- Issues Resolved: ${metrics.issues_resolved}\n- Code Reviews: ${metrics.code_reviews}\n\n**Top Contributors:**\n${top_contributors}"}
        ]
      }

automations:
  - name: "weekly-team-summary"
    description: "Send weekly team summary every Monday at 9 AM"
    enabled: true
    trigger:
      type: "schedule"
      schedule:
        mode: "cron"
        arguments:
          day_of_week: "0"  # Monday
          hour: "9"
          minute: "0"
    default_webhooks: ["team"]
    actions:
      # Fetch task metrics
      - type: "http_request"
        request:
          method: "GET"
          url: "https://project.example.com/api/tasks/weekly-summary"
          headers:
            Authorization: "Bearer ${PROJECT_TOKEN}"
          save_as: "tasks"

      # Fetch team metrics
      - type: "http_request"
        request:
          method: "GET"
          url: "https://project.example.com/api/team/metrics"
          headers:
            Authorization: "Bearer ${PROJECT_TOKEN}"
          save_as: "metrics"

      # Fetch top contributors
      - type: "http_request"
        request:
          method: "GET"
          url: "https://project.example.com/api/team/top-contributors"
          headers:
            Authorization: "Bearer ${PROJECT_TOKEN}"
          save_as: "contributors"

      # Send summary
      - type: "send_template"
        template: "weekly_summary"
        context:
          week_start: "${event_date}"
          tasks: "${tasks}"
          metrics: "${metrics}"
          top_contributors: "${contributors.list}"
```

**Key Features:**

- Runs only on Mondays (day_of_week: "0")
- Aggregates multiple data sources
- Provides team visibility
- Easy to customize for different teams

### Event-Driven Workflows

#### Example 8: Respond to Specific Keywords

Automatically respond to messages containing specific keywords:

```yaml
automations:
  - name: "keyword-responder"
    description: "Respond to messages containing 'help' or 'support'"
    enabled: true
    trigger:
      type: "event"
      event:
        event_type: "im.message.receive_v1"
        conditions:
          - path: "event.message.content"
            operator: "regex"
            value: "(?i)(help|support|urgent)"  # Case-insensitive regex
    default_webhooks: ["support"]
    actions:
      - type: "send_text"
        text: |
          👋 Thanks for reaching out!

          Our support team has been notified and will respond shortly.

          For immediate assistance, visit: https://support.example.com
```

**Key Features:**

- Uses regex for flexible matching
- Case-insensitive pattern matching
- Immediate response to user
- Easy to add more keywords

#### Example 9: Event-Based Escalation

Escalate issues based on event content:

```yaml
templates:
  - name: "escalation_alert"
    type: "card"
    content: |
      {
        "header": {"template": "red", "title": {"tag": "plain_text", "content": "🚨 Issue Escalation"}},
        "elements": [
          {"tag": "markdown", "content": "**Priority:** ${priority}\n**Category:** ${category}\n**Message:** ${message}\n**Timestamp:** ${timestamp}"},
          {"tag": "action", "actions": [{"type": "button", "text": "View Issue", "url": "https://issues.example.com/${issue_id}"}]}
        ]
      }

automations:
  - name: "issue-escalation"
    description: "Escalate critical issues to management"
    enabled: true
    trigger:
      type: "event"
      event:
        event_type: "im.message.receive_v1"
        conditions:
          - path: "event.message.content"
            operator: "contains"
            value: "CRITICAL"
          - path: "event.message.content"
            operator: "contains"
            value: "PRODUCTION"
    default_webhooks: ["escalation"]
    actions:
      # Extract issue details
      - type: "http_request"
        request:
          method: "POST"
          url: "https://issues.example.com/api/parse"
          headers:
            Authorization: "Bearer ${ISSUES_TOKEN}"
            Content-Type: "application/json"
          body:
            message: "${event.message.content}"
          save_as: "parsed"

      # Send escalation alert
      - type: "send_template"
        template: "escalation_alert"
        context:
          priority: "${parsed.priority}"
          category: "${parsed.category}"
          message: "${parsed.message}"
          timestamp: "${event_timestamp}"
          issue_id: "${parsed.issue_id}"
        webhooks: ["escalation"]
```

**Key Features:**

- Multiple conditions (AND logic)
- Parses message content via API
- Sends formatted escalation alert
- Includes link to issue tracker

### Integration Examples

#### Example 10: GitHub Webhook Integration

Process GitHub events and notify team:

```yaml
templates:
  - name: "github_notification"
    type: "card"
    content: |
      {
        "header": {"template": "blue", "title": {"tag": "plain_text", "content": "🐙 GitHub Notification"}},
        "elements": [
          {"tag": "markdown", "content": "**Event:** ${event_type}\n**Repository:** ${repo}\n**Author:** ${author}\n**Details:** ${details}\n\n[View on GitHub](${url})"}
        ]
      }

automations:
  - name: "github-pr-notification"
    description: "Notify team of new pull requests"
    enabled: true
    trigger:
      type: "event"
      event:
        event_type: "im.message.receive_v1"
        conditions:
          - path: "event.message.content"
            operator: "contains"
            value: "github.com"
          - path: "event.message.content"
            operator: "contains"
            value: "pull"
    default_webhooks: ["dev-team"]
    actions:
      # Parse GitHub URL
      - type: "http_request"
        request:
          method: "POST"
          url: "https://api.example.com/parse-github-url"
          headers:
            Content-Type: "application/json"
          body:
            url: "${event.message.content}"
          save_as: "github_info"

      # Fetch PR details from GitHub
      - type: "http_request"
        request:
          method: "GET"
          url: "https://api.github.com/repos/${github_info.owner}/${github_info.repo}/pulls/${github_info.pr_number}"
          headers:
            Authorization: "Bearer ${GITHUB_TOKEN}"
            Accept: "application/vnd.github.v3+json"
          save_as: "pr_details"

      # Send notification
      - type: "send_template"
        template: "github_notification"
        context:
          event_type: "Pull Request"
          repo: "${github_info.repo}"
          author: "${pr_details.user.login}"
          details: "${pr_details.title}"
          url: "${pr_details.html_url}"
```

**Key Features:**

- Parses GitHub URLs from messages
- Fetches PR details from GitHub API
- Sends formatted notification
- Easy to adapt for other events

#### Example 11: Weather-Based Notifications

Send weather alerts based on conditions:

```yaml
templates:
  - name: "weather_alert"
    type: "card"
    content: |
      {
        "header": {"template": "orange", "title": {"tag": "plain_text", "content": "🌤️ Weather Alert"}},
        "elements": [
          {"tag": "markdown", "content": "**Location:** ${location}\n**Condition:** ${condition}\n**Temperature:** ${temp}°C\n**Humidity:** ${humidity}%\n**Wind:** ${wind_speed} km/h\n\n**Alert:** ${alert_message}"}
        ]
      }

automations:
  - name: "weather-alert"
    description: "Send weather alerts for extreme conditions"
    enabled: true
    trigger:
      type: "schedule"
      schedule:
        mode: "cron"
        arguments:
          hour: "6,12,18"  # 6 AM, 12 PM, 6 PM
          minute: "0"
    default_webhooks: ["notifications"]
    actions:
      # Fetch weather data
      - type: "http_request"
        request:
          method: "GET"
          url: "https://api.openweathermap.org/data/2.5/weather?q=Shanghai&appid=${WEATHER_API_KEY}&units=metric"
          save_as: "weather"

      # Send alert if conditions are extreme
      - type: "send_template"
        template: "weather_alert"
        context:
          location: "Shanghai"
          condition: "${weather.weather[0].main}"
          temp: "${weather.main.temp}"
          humidity: "${weather.main.humidity}"
          wind_speed: "${weather.wind.speed}"
          alert_message: "⚠️ Extreme weather conditions detected. Please take precautions."
```

**Key Features:**

- Runs at multiple times per day
- Fetches real-time weather data
- Sends formatted alert
- Easy to add multiple locations

#### Example 12: Status Page Monitoring

Monitor status page and alert on incidents:

```yaml
templates:
  - name: "incident_alert"
    type: "card"
    content: |
      {
        "header": {"template": "red", "title": {"tag": "plain_text", "content": "🚨 Incident Alert"}},
        "elements": [
          {"tag": "markdown", "content": "**Status:** ${status}\n**Component:** ${component}\n**Impact:** ${impact}\n**Started:** ${started_at}\n\n**Description:** ${description}\n\n[View Status Page](${status_page_url})"}
        ]
      }

automations:
  - name: "status-page-monitor"
    description: "Monitor status page for incidents every 5 minutes"
    enabled: true
    trigger:
      type: "schedule"
      schedule:
        mode: "cron"
        arguments:
          minute: "*/5"
    default_webhooks: ["incidents"]
    actions:
      # Fetch current incidents
      - type: "http_request"
        request:
          method: "GET"
          url: "https://status.example.com/api/v2/incidents/unresolved"
          headers:
            Authorization: "Bearer ${STATUS_PAGE_TOKEN}"
          save_as: "incidents"

      # Send alert if incidents exist
      - type: "send_template"
        template: "incident_alert"
        context:
          status: "${incidents.incidents[0].status}"
          component: "${incidents.incidents[0].components[0].name}"
          impact: "${incidents.incidents[0].impact}"
          started_at: "${incidents.incidents[0].created_at}"
          description: "${incidents.incidents[0].name}"
          status_page_url: "https://status.example.com"
```

**Key Features:**

- Monitors external status page
- Checks for unresolved incidents
- Sends immediate alerts
- Includes link to status page

## Advanced Features

### Chaining Multiple HTTP Requests

Chain multiple HTTP requests and use results from previous requests in subsequent ones:

```yaml
automations:
  - name: "multi-step-data-pipeline"
    description: "Fetch data from multiple sources and aggregate"
    enabled: true
    trigger:
      type: "schedule"
      schedule:
        mode: "cron"
        arguments: { hour: "9", minute: "0" }
    actions:
      # Step 1: Get user list
      - type: "http_request"
        request:
          method: "GET"
          url: "https://api.example.com/users?active=true"
          headers:
            Authorization: "Bearer ${API_TOKEN}"
          save_as: "users"

      # Step 2: Get stats for each user (using first user as example)
      - type: "http_request"
        request:
          method: "GET"
          url: "https://api.example.com/users/${users.data[0].id}/stats"
          headers:
            Authorization: "Bearer ${API_TOKEN}"
          save_as: "user_stats"

      # Step 3: Get activity log
      - type: "http_request"
        request:
          method: "GET"
          url: "https://api.example.com/activity?limit=10"
          headers:
            Authorization: "Bearer ${API_TOKEN}"
          save_as: "activity"

      # Step 4: Send aggregated report
      - type: "send_text"
        text: |
          📊 Daily Data Report

          Active Users: ${users.count}
          Top User: ${users.data[0].name}
          User Stats: ${user_stats}
          Recent Activity: ${activity.count} events
```

### Using Context Variables from Previous Actions

Access and manipulate data from previous HTTP requests:

```yaml
automations:
  - name: "context-aware-workflow"
    description: "Use context variables to make decisions"
    enabled: true
    trigger:
      type: "schedule"
      schedule:
        mode: "cron"
        arguments: { hour: "*/2", minute: "0" }  # Every 2 hours
    actions:
      # Fetch metrics
      - type: "http_request"
        request:
          method: "GET"
          url: "https://metrics.example.com/api/current"
          save_as: "metrics"

      # Use metrics data in template
      - type: "send_template"
        template: "metrics_card"
        context:
          cpu_usage: "${metrics.cpu}"
          memory_usage: "${metrics.memory}"
          disk_usage: "${metrics.disk}"
          timestamp: "${event_timestamp}"
          status: "${metrics.status}"
```

### Conditional Logic with Event Filters

Use multiple conditions to filter events:

```yaml
automations:
  - name: "conditional-event-handler"
    description: "Handle events with multiple conditions"
    enabled: true
    trigger:
      type: "event"
      event:
        event_type: "im.message.receive_v1"
        conditions:
          # All conditions must be true (AND logic)
          - path: "event.message.content"
            operator: "contains"
            value: "deploy"
          - path: "event.message.content"
            operator: "contains"
            value: "production"
          - path: "event.sender.user_id"
            operator: "equals"
            value: "ou_xxx"  # Specific user ID
    actions:
      - type: "send_text"
        text: "🚀 Production deployment request received from authorized user"
```

### Error Handling and Retry Strategies

Configure HTTP requests with timeout and retry logic:

```yaml
automations:
  - name: "resilient-http-requests"
    description: "Handle failures gracefully"
    enabled: true
    trigger:
      type: "schedule"
      schedule:
        mode: "cron"
        arguments: { hour: "*/1", minute: "0" }  # Every hour
    actions:
      # HTTP request with timeout
      - type: "http_request"
        request:
          method: "GET"
          url: "https://api.example.com/data"
          timeout: 5  # 5 second timeout
          headers:
            Authorization: "Bearer ${API_TOKEN}"
          save_as: "data"

      # Send result or error message
      - type: "send_text"
        text: |
          API Response Status: ${data.status}
          Data Retrieved: ${data.count} records
          Timestamp: ${event_timestamp}
```

### Template Rendering with Complex Data

Use templates to format complex nested data:

```yaml
templates:
  - name: "complex_report"
    type: "card"
    engine: "string"
    content: |
      {
        "header": {"template": "blue", "title": {"tag": "plain_text", "content": "Complex Data Report"}},
        "elements": [
          {
            "tag": "markdown",
            "content": "**Report Date:** ${date}\n\n**Departments:**\n${departments}\n\n**Summary:**\nTotal: ${total}\nAverage: ${average}\nStatus: ${status}"
          }
        ]
      }

automations:
  - name: "complex-template-rendering"
    description: "Render complex nested data in templates"
    enabled: true
    trigger:
      type: "schedule"
      schedule:
        mode: "cron"
        arguments: { day_of_week: "1", hour: "9", minute: "0" }  # Monday 9 AM
    actions:
      # Fetch complex data
      - type: "http_request"
        request:
          method: "GET"
          url: "https://api.example.com/departments/report"
          headers:
            Authorization: "Bearer ${API_TOKEN}"
          save_as: "report"

      # Render with template
      - type: "send_template"
        template: "complex_report"
        context:
          date: "${event_date}"
          departments: "${report.departments}"
          total: "${report.total}"
          average: "${report.average}"
          status: "${report.status}"
```

## Best Practices

1. **Use meaningful names** - Give automations descriptive names that indicate their purpose
2. **Add descriptions** - Document what each automation does for future reference
3. **Test schedules** - Verify cron expressions work as expected using online cron validators
4. **Handle errors** - Configure appropriate timeouts and error handling for HTTP requests
5. **Use templates** - Reuse templates for consistent formatting across automations
6. **Limit frequency** - Avoid too frequent automations to prevent spam and API rate limits
7. **Monitor logs** - Check logs for automation execution and errors
8. **Use environment variables** - Store sensitive data (API tokens, URLs) in environment variables
9. **Chain requests wisely** - Avoid excessive chaining that could slow down automation execution
10. **Test with dry runs** - Disable automations initially and test with manual triggers
11. **Document context variables** - Keep track of what data is available at each step
12. **Use meaningful webhook names** - Organize webhooks by purpose (alerts, reports, notifications)

## Common Patterns

### Pattern 1: Scheduled Notifications

Send regular notifications at specific times:

```yaml
automations:
  - name: "morning-standup-reminder"
    description: "Remind team for daily standup"
    enabled: true
    trigger:
      type: "schedule"
      schedule:
        mode: "cron"
        arguments:
          day_of_week: "mon-fri"
          hour: "9"
          minute: "30"
    default_webhooks: ["team"]
    actions:
      - type: "send_text"
        text: |
          🎯 Daily Standup Reminder

          Time: 10:00 AM
          Location: Conference Room A
          Duration: 15 minutes

          Please be ready to share:
          - What you completed yesterday
          - What you're working on today
          - Any blockers
```

### Pattern 2: Status Aggregation

Collect status from multiple sources and send summary:

```yaml
automations:
  - name: "infrastructure-status"
    description: "Check all infrastructure components"
    enabled: true
    trigger:
      type: "schedule"
      schedule:
        mode: "cron"
        arguments:
          minute: "*/15"  # Every 15 minutes
    actions:
      - type: "http_request"
        request:
          method: "GET"
          url: "https://api.example.com/health/database"
          timeout: 3
          save_as: "db"

      - type: "http_request"
        request:
          method: "GET"
          url: "https://api.example.com/health/cache"
          timeout: 3
          save_as: "cache"

      - type: "http_request"
        request:
          method: "GET"
          url: "https://api.example.com/health/queue"
          timeout: 3
          save_as: "queue"

      - type: "send_text"
        text: |
          🏗️ Infrastructure Status

          Database: ${db.status}
          Cache: ${cache.status}
          Queue: ${queue.status}

          Last checked: ${event_time}
```

### Pattern 3: Event-Triggered Notifications

React to specific events and send notifications:

```yaml
automations:
  - name: "deployment-notification"
    description: "Notify on deployment events"
    enabled: true
    trigger:
      type: "event"
      event:
        event_type: "im.message.receive_v1"
        conditions:
          - path: "event.message.content"
            operator: "regex"
            value: "deployed|deployment|release"
    actions:
      - type: "send_text"
        text: |
          🚀 Deployment Notification

          Message: ${event.message.content}
          Time: ${event_timestamp}

          Please monitor the application for any issues.
```

### Pattern 4: Data Collection and Reporting

Collect data from multiple sources and generate reports:

```yaml
automations:
  - name: "weekly-performance-report"
    description: "Generate weekly performance report"
    enabled: true
    trigger:
      type: "schedule"
      schedule:
        mode: "cron"
        arguments:
          day_of_week: "5"  # Friday
          hour: "17"
          minute: "0"
    actions:
      - type: "http_request"
        request:
          method: "GET"
          url: "https://analytics.example.com/api/weekly-stats"
          headers:
            Authorization: "Bearer ${ANALYTICS_TOKEN}"
          save_as: "stats"

      - type: "http_request"
        request:
          method: "GET"
          url: "https://analytics.example.com/api/user-engagement"
          headers:
            Authorization: "Bearer ${ANALYTICS_TOKEN}"
          save_as: "engagement"

      - type: "send_template"
        template: "weekly_report"
        context:
          week: "${event_date}"
          stats: "${stats}"
          engagement: "${engagement}"
```

### Pattern 5: Conditional Alerts

Send alerts only when conditions are met:

```yaml
automations:
  - name: "error-rate-alert"
    description: "Alert when error rate exceeds threshold"
    enabled: true
    trigger:
      type: "schedule"
      schedule:
        mode: "cron"
        arguments:
          minute: "*/5"
    actions:
      - type: "http_request"
        request:
          method: "GET"
          url: "https://monitoring.example.com/api/error-rate"
          save_as: "metrics"

      - type: "send_text"
        text: |
          ⚠️ Error Rate Alert

          Current Error Rate: ${metrics.error_rate}%
          Threshold: 5%
          Status: ${metrics.status}

          Action Required: Please investigate immediately
```

## Troubleshooting

### Automation not triggering

- Check that `enabled: true`
- Verify cron expression syntax
- Check logs for errors
- Ensure event server is running (for event triggers)

### Template rendering fails

- Verify template name matches
- Check variable names in context
- Ensure template engine is correct

### HTTP request fails

- Check URL is accessible
- Verify headers and authentication
- Check response format matches expectations

## Tips & Tricks

### Using Cron Expressions Effectively

**Every N minutes:**

```yaml
minute: "*/5"  # Every 5 minutes
minute: "*/15" # Every 15 minutes
minute: "*/30" # Every 30 minutes
```

**Specific times:**

```yaml
hour: "9,12,15,18"  # 9 AM, 12 PM, 3 PM, 6 PM
minute: "0,30"      # On the hour and half-hour
```

**Business hours:**

```yaml
day_of_week: "mon-fri"  # Monday to Friday
hour: "9-17"            # 9 AM to 5 PM
```

**Monthly:**

```yaml
day: "1"   # First day of month
day: "15"  # 15th of month
```

### Debugging Automations

1. **Enable logging** - Set log level to DEBUG in config
2. **Check automation logs** - Look for execution timestamps and errors
3. **Test with manual trigger** - Temporarily set a frequent schedule to test
4. **Validate JSON** - Use online JSON validators for template content
5. **Test API endpoints** - Use curl or Postman to verify API responses

### Performance Optimization

1. **Reduce frequency** - Don't run automations more often than necessary
2. **Use appropriate timeouts** - Set reasonable timeouts to avoid hanging requests
3. **Batch operations** - Combine multiple small automations into one
4. **Cache results** - Store frequently accessed data to reduce API calls
5. **Limit data size** - Request only necessary fields from APIs

### Security Best Practices

1. **Use environment variables** - Never hardcode API tokens or secrets
2. **Validate inputs** - Use conditions to filter untrusted event data
3. **Use HTTPS** - Always use HTTPS for API endpoints
4. **Rotate tokens** - Regularly rotate API tokens and secrets
5. **Limit permissions** - Use API tokens with minimal required permissions
6. **Monitor execution** - Review logs for suspicious activity

### Template Tips

1. **Use meaningful variable names** - Make templates self-documenting
2. **Format dates consistently** - Use ISO 8601 format (YYYY-MM-DD)
3. **Include timestamps** - Add event_timestamp to track when automation ran
4. **Use emojis** - Make messages more visually appealing
5. **Add action buttons** - Include links to dashboards or issue trackers
6. **Test rendering** - Verify templates with sample data before deploying

### Webhook Organization

Organize webhooks by purpose:

```yaml
webhooks:
  - name: "alerts"
    url: "https://..."  # For critical alerts

  - name: "reports"
    url: "https://..."  # For scheduled reports

  - name: "notifications"
    url: "https://..."  # For general notifications

  - name: "dev-team"
    url: "https://..."  # For development team
```

Then use appropriate webhook in each automation:

```yaml
automations:
  - name: "critical-alert"
    actions:
      - type: "send_text"
        webhooks: ["alerts"]  # Use alerts webhook

  - name: "daily-report"
    actions:
      - type: "send_text"
        webhooks: ["reports"]  # Use reports webhook
```

### Testing Automations Safely

1. **Start disabled** - Create automations with `enabled: false`
2. **Use test webhook** - Point to a test channel initially
3. **Set frequent schedule** - Use `minute: "*/1"` to test quickly
4. **Monitor execution** - Watch logs during test period
5. **Enable gradually** - Move to production webhook after testing
6. **Set normal schedule** - Update cron expression for production

### Handling Large Responses

When APIs return large responses:

```yaml
actions:
  - type: "http_request"
    request:
      method: "GET"
      url: "https://api.example.com/data?limit=10"  # Limit results
      headers:
        Authorization: "Bearer ${API_TOKEN}"
      save_as: "data"

  - type: "send_text"
    text: |
      Results: ${data.count}
      First item: ${data.items[0].name}
      Last updated: ${event_timestamp}
```

### Combining Multiple Conditions

Use multiple conditions for complex filtering:

```yaml
trigger:
  type: "event"
  event:
    event_type: "im.message.receive_v1"
    conditions:
      # All must be true (AND logic)
      - path: "event.message.content"
        operator: "contains"
        value: "bug"

      - path: "event.message.content"
        operator: "contains"
        value: "critical"

      - path: "event.sender.user_id"
        operator: "equals"
        value: "ou_xxx"
```

### Reusing Templates Across Automations

Define templates once and use in multiple automations:

```yaml
templates:
  - name: "alert_card"
    type: "card"
    content: |
      {
        "header": {"template": "red", "title": {"tag": "plain_text", "content": "⚠️ Alert"}},
        "elements": [{"tag": "markdown", "content": "${message}"}]
      }

automations:
  - name: "alert-1"
    actions:
      - type: "send_template"
        template: "alert_card"
        context:
          message: "Alert 1 message"

  - name: "alert-2"
    actions:
      - type: "send_template"
        template: "alert_card"
        context:
          message: "Alert 2 message"
```
