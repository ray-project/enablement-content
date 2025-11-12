# Multi-Actor Ray Serve Tracing Example

A demonstration of distributed tracing across multiple Ray Serve actors using OpenTelemetry. This example shows how to trace requests that flow through multiple services in a microservices architecture built with Ray Serve.

## Overview

This project implements a multi-service application with the following components:

- **APIGateway**: Main entry point handling HTTP requests
- **UserService**: Orchestrates user-related operations
- **DatabaseService**: Simulates database operations
- **NotificationService**: Handles email notifications

All services are instrumented with OpenTelemetry to provide distributed tracing capabilities.

## Architecture

```
APIGateway
├── UserService
    ├── DatabaseService
    └── NotificationService
```

## Request Flow

The application demonstrates two main request flows:

### 1. User Profile Retrieval
```
GET /user/{user_id}
APIGateway → UserService → DatabaseService
```

### 2. User Registration
```
POST /register
APIGateway → UserService → DatabaseService + NotificationService
```

## Trace Structure

Each request generates traces showing the complete journey:

```
proxy_http_request (Root)
   └── proxy_route_to_replica (APIGateway)
       └── replica_handle_request (APIGateway) 
           └── proxy_route_to_replica (UserService)
               └── replica_handle_request (UserService)
                   └── proxy_route_to_replica (DatabaseService)
                       └── replica_handle_request (DatabaseService)
```

## Setup and Installation

### Prerequisites

- Ray 2.40.0 or later
- Python 3.10+
- Anyscale CLI (for deployment)

### Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run locally with Ray Serve:
```bash
serve run multi_actor_tracing_ray_serve_example:app
```

## Deployment

Deploy to Anyscale using the provided service configuration:

```bash
anyscale service deploy -f default_tracing_service.yaml
```

## API Endpoints

> **Important**: After querying your application, Anyscale exports traces to the `/tmp/ray/session_latest/logs/serve/spans/` folder on instances with active replicas. You can access these traces by navigating to your service in the Anyscale console, opening a terminal session, and browsing to the specified directory.

### Available Endpoints

1. **GET /** - Service information and available endpoints
2. **GET /user/{user_id}** - Retrieve user profile
3. **POST /register** - Register a new user
4. **GET /health** - Health check endpoint

### Sample Requests

#### Get User Profile
```bash
curl -H "Authorization: Bearer <token>" https://my-service.anyscale.com/user/1
```

**Example Response:**
```json
{
  "success": true,
  "data": {
    "user": {
      "id": "1",
      "name": "Alice",
      "email": "alice@example.com"
    },
    "profile_data": {
      "last_login": "2024-08-29T10:00:00Z",
      "preferences": {
        "theme": "dark",
        "notifications": true
      }
    },
    "timestamp": 1693310400.123
  }
}
```

**Generated Trace Structure:**
```
1. proxy_http_request (Root) - Duration: 245ms
   └── 2. proxy_route_to_replica (APIGateway) - Duration: 240ms
       └── 3. replica_handle_request (APIGateway) - Duration: 235ms
           └── 4. proxy_route_to_replica (UserService) - Duration: 180ms
               └── 5. replica_handle_request (UserService) - Duration: 175ms
                   └── 6. proxy_route_to_replica (DatabaseService) - Duration: 110ms
                       └── 7. replica_handle_request (DatabaseService) - Duration: 105ms
```

**Trace Details:**
- **Span 1**: HTTP request enters Ray Serve proxy
- **Span 2-3**: Request routed to and handled by APIGateway actor
- **Span 4-5**: APIGateway calls UserService actor via `get_user_profile.remote()`
- **Span 6-7**: UserService calls DatabaseService actor via `get_user.remote()`

Response traces: APIGateway → UserService → DatabaseService

#### Register New User
```bash
curl -X POST -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
  -d '{"name": "David", "email": "david@example.com"}' https://my-service.anyscale.com/register
```

**Example Response:**
```json
{
  "success": true,
  "data": {
    "user": {
      "id": "4",
      "name": "David",
      "email": "david@example.com"
    },
    "notification": {
      "status": "sent",
      "message": "Welcome David! Thanks for joining our service.",
      "recipient": "david@example.com"
    },
    "registration_complete": true,
    "timestamp": 1693310400.456
  }
}
```

**Generated Trace Structure:**
```
1. proxy_http_request (Root) - Duration: 485ms
   └── 2. proxy_route_to_replica (APIGateway) - Duration: 480ms
       └── 3. replica_handle_request (APIGateway) - Duration: 475ms
           └── 4. proxy_route_to_replica (UserService) - Duration: 420ms
               └── 5. replica_handle_request (UserService) - Duration: 415ms
                   ├── 6. proxy_route_to_replica (DatabaseService) - Duration: 210ms
                   │   └── 7. replica_handle_request (DatabaseService) - Duration: 205ms
                   └── 8. proxy_route_to_replica (NotificationService) - Duration: 155ms
                       └── 9. replica_handle_request (NotificationService) - Duration: 150ms
```

**Trace Details:**
- **Span 1**: HTTP POST request enters Ray Serve proxy
- **Span 2-3**: Request routed to and handled by APIGateway actor
- **Span 4-5**: APIGateway calls UserService actor via `register_user.remote()`
- **Span 6-7**: UserService calls DatabaseService actor via `create_user.remote()` (200ms DB write)
- **Span 8-9**: UserService calls NotificationService actor via `send_welcome_email.remote()` (150ms email send)

Response traces: APIGateway → UserService → DatabaseService + NotificationService

## Tracing Configuration

The service is configured with comprehensive tracing:

- **Enabled**: `True`
- **Sampling Ratio**: `1.0` (100% of requests traced)
- **OpenTelemetry Instrumentation**: FastAPI, ASGI
- **Export Format**: OTLP (OpenTelemetry Protocol)

