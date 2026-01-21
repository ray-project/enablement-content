#json_method1.py
from openai import OpenAI
from pydantic import BaseModel
from enum import Enum

client = OpenAI(base_url="http://localhost:8000/v1", api_key="FAKE_KEY")

# (Optional) We use Pydantic model to handle schema definition/validation
class CarType(str, Enum):
    sedan = "sedan"
    suv = "SUV"
    truck = "Truck"
    coupe = "Coupe"

class CarDescription(BaseModel):
    brand: str
    model: str
    car_type: CarType

# 1. Define your schema
json_schema = CarDescription.model_json_schema()

# 2. Send a request
response = client.chat.completions.create(
    model="my-qwen",
    messages=[
        {
            "role": "user",
            "content": "Generate a JSON with the brand, model and car_type of the most iconic car from the 90's",
        }
    ],
    # 3. Set `response_format` of type `json_schema`
    response_format= {
        "type": "json_schema",
        # 4. Provide `name`and `schema` (both required)
        "json_schema": {
            "name": "car-description", # arbitrary
            "schema": json_schema # your JSON schema
        },
    }
)

print(response.choices[0].message.content)