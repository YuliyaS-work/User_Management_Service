# Authentication and Authorization Service
 
## Description
 
This project is a microservice for user authentication and authorization. It provides secure user login, access token generation, refresh token management, and user permission control.
 
The service is built with FastAPI and follows a microservice architecture. It uses JWT tokens for authentication and RabbitMQ for publishing internal events.
 
## Features
 
- User authentication
- JWT access and refresh tokens
- Role-based authorization
- Password validation
- Database migrations with Alembic
- Event publishing with RabbitMQ
- Redis caching and token storage
- REST API with FastAPI
- Automated testing
- CI/CD with GitHub Actions
 
## Technology Stack
 
### Backend
- FastAPI
- Python Asyncio
- SQLAlchemy 2.0
- Pydantic
- Alembic
- AsyncPG
- Redis
- JWT (PyJWT / Python-JOSE)
- AioPika
- AioBoto3
- Poetry
 
### Databases
- PostgreSQL
- Redis
 
### Message Broker
- RabbitMQ
 
### Cloud Services
- AWS S3
 
### CI/CD
- GitHub Actions
 
## Project Workflow
 
The project includes:
 
- Poetry project setup
- Docker and Docker Compose configuration
- Environment settings with Pydantic Settings
- Database models with SQLAlchemy 2.0
- Database migrations with Alembic
- Data validation with Pydantic
- API endpoints separated into FastAPI routers
- Dependency Injection with FastAPI Depends
- Custom error handling
- RabbitMQ message publishing
- JWT authentication and authorization
- Unit and integration tests with Pytest
- Automated build, lint, and test pipelines using GitHub Actions
 
## Testing
Tests are automatically executed by GitHub Actions on every push and pull request.
 
The CI pipeline includes:
- Automated test execution
- Code quality checks
- Build validation
