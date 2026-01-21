from fastapi import FastAPI, HTTPException
from ray import serve
import asyncio
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Multi-Actor Tracing Example")

@serve.deployment
class DatabaseService:
    """Simulates database operations"""
    
    def __init__(self):
        self.users = {
            "1": {"id": "1", "name": "Alice", "email": "alice@example.com"},
            "2": {"id": "2", "name": "Bob", "email": "bob@example.com"},
            "3": {"id": "3", "name": "Charlie", "email": "charlie@example.com"}
        }
        logger.info("DatabaseService initialized")
    
    async def get_user(self, user_id: str):
        """Get user by ID with simulated DB delay"""
        logger.info(f"DatabaseService: Getting user {user_id}")
        # Simulate database query time
        await asyncio.sleep(0.1)
        
        if user_id not in self.users:
            raise HTTPException(status_code=404, detail="User not found")
        
        user = self.users[user_id]
        logger.info(f"DatabaseService: Retrieved user {user['name']}")
        return user
    
    async def create_user(self, user_data: dict):
        """Create a new user"""
        logger.info(f"DatabaseService: Creating user {user_data.get('name')}")
        await asyncio.sleep(0.2)  # Simulate DB write time
        
        user_id = str(len(self.users) + 1)
        user_data["id"] = user_id
        self.users[user_id] = user_data
        
        logger.info(f"DatabaseService: Created user {user_id}")
        return user_data

@serve.deployment
class NotificationService:
    """Simulates notification sending"""
    
    def __init__(self):
        logger.info("NotificationService initialized")
    
    async def send_welcome_email(self, user_email: str, user_name: str):
        """Send welcome email notification"""
        logger.info(f"NotificationService: Sending welcome email to {user_email}")
        # Simulate email sending time
        await asyncio.sleep(0.15)
        
        message = f"Welcome {user_name}! Thanks for joining our service."
        logger.info(f"NotificationService: Email sent to {user_email}")
        return {"status": "sent", "message": message, "recipient": user_email}

@serve.deployment
class UserService:
    """Main user service that coordinates other services"""
    
    def __init__(self, db_handle, notification_handle):
        self.db_service = db_handle
        self.notification_service = notification_handle
        logger.info("UserService initialized")
    
    async def get_user_profile(self, user_id: str):
        """Get complete user profile"""
        logger.info(f"UserService: Getting profile for user {user_id}")
        
        # Call database service
        user = await self.db_service.get_user.remote(user_id)
        
        profile = {
            "user": user,
            "profile_data": {
                "last_login": "2024-08-29T10:00:00Z",
                "preferences": {"theme": "dark", "notifications": True}
            },
            "timestamp": time.time()
        }
        
        logger.info(f"UserService: Profile retrieved for {user['name']}")
        return profile
    
    async def register_user(self, user_data: dict):
        """Register a new user and send welcome notification"""
        logger.info(f"UserService: Registering user {user_data.get('name')}")
        
        # Create user in database
        user = await self.db_service.create_user.remote(user_data)
        
        # Send welcome notification
        notification_result = await self.notification_service.send_welcome_email.remote(
            user["email"], user["name"]
        )
        
        result = {
            "user": user,
            "notification": notification_result,
            "registration_complete": True,
            "timestamp": time.time()
        }
        
        logger.info(f"UserService: User {user['name']} registered successfully")
        return result

@serve.deployment
@serve.ingress(app)
class APIGateway:
    """Main API gateway that handles HTTP requests"""
    
    def __init__(self, user_service_handle):
        self.user_service = user_service_handle
        logger.info("APIGateway initialized")
    
    @app.get("/")
    async def root(self):  # FIXED: Added self parameter
        return {"message": "Multi-Actor Tracing API", "endpoints": ["/user/{user_id}", "/register"]}
    
    @app.get("/user/{user_id}")
    async def get_user(self, user_id: str):
        """Get user profile endpoint"""
        logger.info(f"APIGateway: GET /user/{user_id}")
        try:
            profile = await self.user_service.get_user_profile.remote(user_id)
            return {"success": True, "data": profile}
        except Exception as e:
            logger.error(f"APIGateway: Error getting user {user_id}: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/register")
    async def register_user(self, user_data: dict):
        """Register new user endpoint"""
        logger.info(f"APIGateway: POST /register for {user_data.get('name')}")
        try:
            result = await self.user_service.register_user.remote(user_data)
            return {"success": True, "data": result}
        except Exception as e:
            logger.error(f"APIGateway: Error registering user: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/health")
    async def health_check(self):
        """Health check endpoint"""
        return {"status": "healthy", "timestamp": time.time()}

# Create the application graph
db_service = DatabaseService.bind()
notification_service = NotificationService.bind()
user_service = UserService.bind(db_service, notification_service)
app = APIGateway.bind(user_service)

