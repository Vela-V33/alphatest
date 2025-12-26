#!/usr/bin/env python3
"""
Test Data Management Module
Provides fixtures, seed data, and test data generation capabilities.
"""

import json
import random
import string
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from faker import Faker


class TestDataManager:
    """Manages test data, fixtures, and seed data for testing."""

    def __init__(self, project_dir: Path):
        """
        Initialize test data manager.

        Args:
            project_dir: Path to project directory for storing fixtures
        """
        self.project_dir = Path(project_dir)
        self.fixtures_dir = self.project_dir / "fixtures"
        self.fixtures_dir.mkdir(parents=True, exist_ok=True)
        self.faker = Faker()

        # Load existing fixtures
        self.fixtures = {}
        self._load_fixtures()

    def _load_fixtures(self):
        """Load all fixture files from fixtures directory."""
        for fixture_file in self.fixtures_dir.glob("*.json"):
            try:
                fixture_name = fixture_file.stem
                data = json.loads(fixture_file.read_text())
                self.fixtures[fixture_name] = data
            except Exception as e:
                print(f"Error loading fixture {fixture_file}: {e}")

    def save_fixture(self, name: str, data: Any) -> bool:
        """
        Save data as a reusable fixture.

        Args:
            name: Name of the fixture
            data: Data to save

        Returns:
            True if saved successfully
        """
        try:
            fixture_path = self.fixtures_dir / f"{name}.json"
            fixture_path.write_text(json.dumps(data, indent=2))
            self.fixtures[name] = data
            return True
        except Exception as e:
            print(f"Error saving fixture: {e}")
            return False

    def get_fixture(self, name: str) -> Optional[Any]:
        """
        Get a fixture by name.

        Args:
            name: Name of the fixture

        Returns:
            Fixture data or None if not found
        """
        return self.fixtures.get(name)

    def delete_fixture(self, name: str) -> bool:
        """
        Delete a fixture.

        Args:
            name: Name of fixture to delete

        Returns:
            True if deleted successfully
        """
        try:
            fixture_path = self.fixtures_dir / f"{name}.json"
            if fixture_path.exists():
                fixture_path.unlink()
            if name in self.fixtures:
                del self.fixtures[name]
            return True
        except Exception as e:
            print(f"Error deleting fixture: {e}")
            return False

    def list_fixtures(self) -> List[str]:
        """
        Get list of all available fixtures.

        Returns:
            List of fixture names
        """
        return list(self.fixtures.keys())

    # Data Generators

    def generate_user(self, role: str = 'user') -> Dict:
        """Generate realistic user data."""
        return {
            'first_name': self.faker.first_name(),
            'last_name': self.faker.last_name(),
            'email': self.faker.email(),
            'username': self.faker.user_name(),
            'password': self.faker.password(length=12),
            'phone': self.faker.phone_number(),
            'role': role,
            'created_at': datetime.now().isoformat()
        }

    def generate_address(self) -> Dict:
        """Generate realistic address data."""
        return {
            'street': self.faker.street_address(),
            'city': self.faker.city(),
            'state': self.faker.state_abbr(),
            'zip': self.faker.zipcode(),
            'country': self.faker.country_code()
        }

    def generate_company(self) -> Dict:
        """Generate realistic company data."""
        return {
            'name': self.faker.company(),
            'email': self.faker.company_email(),
            'phone': self.faker.phone_number(),
            'website': self.faker.url(),
            'industry': random.choice(['Technology', 'Finance', 'Healthcare', 'Retail', 'Manufacturing'])
        }

    def generate_product(self) -> Dict:
        """Generate realistic product data."""
        return {
            'name': self.faker.catch_phrase(),
            'description': self.faker.text(max_nb_chars=200),
            'price': round(random.uniform(9.99, 999.99), 2),
            'sku': self.faker.ean13(),
            'category': random.choice(['Electronics', 'Clothing', 'Books', 'Home', 'Sports']),
            'stock': random.randint(0, 1000),
            'created_at': datetime.now().isoformat()
        }

    def generate_credit_card(self) -> Dict:
        """Generate test credit card data."""
        return {
            'number': self.faker.credit_card_number(),
            'cvv': self.faker.credit_card_security_code(),
            'expiry': self.faker.credit_card_expire(),
            'name': self.faker.name()
        }

    def generate_lorem(self, paragraphs: int = 3) -> str:
        """Generate lorem ipsum text."""
        return '\n\n'.join(self.faker.paragraphs(nb=paragraphs))

    def generate_date(self, past: bool = True, days: int = 365) -> str:
        """
        Generate random date.

        Args:
            past: If True, generate past date, otherwise future
            days: Number of days in the past/future

        Returns:
            ISO format date string
        """
        if past:
            date = datetime.now() - timedelta(days=random.randint(0, days))
        else:
            date = datetime.now() + timedelta(days=random.randint(0, days))
        return date.isoformat()

    def generate_random_string(self, length: int = 10, chars: str = None) -> str:
        """
        Generate random string.

        Args:
            length: Length of string
            chars: Character set to use

        Returns:
            Random string
        """
        if chars is None:
            chars = string.ascii_letters + string.digits
        return ''.join(random.choice(chars) for _ in range(length))

    def generate_email(self, domain: str = None) -> str:
        """
        Generate email address.

        Args:
            domain: Optional domain to use

        Returns:
            Email address
        """
        if domain:
            username = self.faker.user_name()
            return f"{username}@{domain}"
        return self.faker.email()

    # Seed Data Management

    def create_seed_data(self, entity_type: str, count: int = 10) -> List[Dict]:
        """
        Create seed data for an entity type.

        Args:
            entity_type: Type of entity (user, product, company, etc.)
            count: Number of entities to generate

        Returns:
            List of generated entities
        """
        generators = {
            'user': self.generate_user,
            'address': self.generate_address,
            'company': self.generate_company,
            'product': self.generate_product,
            'credit_card': self.generate_credit_card
        }

        generator = generators.get(entity_type)
        if not generator:
            raise ValueError(f"Unknown entity type: {entity_type}")

        return [generator() for _ in range(count)]

    def save_seed_data(self, name: str, entity_type: str, count: int = 10) -> bool:
        """
        Generate and save seed data as a fixture.

        Args:
            name: Name for the seed data fixture
            entity_type: Type of entity to generate
            count: Number of entities

        Returns:
            True if saved successfully
        """
        seed_data = self.create_seed_data(entity_type, count)
        return self.save_fixture(name, seed_data)

    # Data Builders (Fluent API)

    class DataBuilder:
        """Fluent API for building test data."""

        def __init__(self, manager: 'TestDataManager'):
            self.manager = manager
            self.data = {}

        def with_user(self, role: str = 'user') -> 'TestDataManager.DataBuilder':
            """Add user data."""
            self.data['user'] = self.manager.generate_user(role)
            return self

        def with_address(self) -> 'TestDataManager.DataBuilder':
            """Add address data."""
            self.data['address'] = self.manager.generate_address()
            return self

        def with_company(self) -> 'TestDataManager.DataBuilder':
            """Add company data."""
            self.data['company'] = self.manager.generate_company()
            return self

        def with_product(self) -> 'TestDataManager.DataBuilder':
            """Add product data."""
            self.data['product'] = self.manager.generate_product()
            return self

        def with_field(self, key: str, value: Any) -> 'TestDataManager.DataBuilder':
            """Add custom field."""
            self.data[key] = value
            return self

        def build(self) -> Dict:
            """Build and return the data."""
            return self.data

    def builder(self) -> DataBuilder:
        """Create a new data builder."""
        return self.DataBuilder(self)


# Faker isn't a standard library, so let's create a simple fallback
class SimpleFaker:
    """Simple faker implementation if faker library not available."""

    @staticmethod
    def first_name():
        return random.choice(['John', 'Jane', 'Bob', 'Alice', 'Charlie', 'Diana'])

    @staticmethod
    def last_name():
        return random.choice(['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia'])

    @staticmethod
    def email():
        names = ['user', 'test', 'demo', 'sample']
        domains = ['example.com', 'test.com', 'demo.com']
        return f"{random.choice(names)}{random.randint(1, 999)}@{random.choice(domains)}"

    @staticmethod
    def user_name():
        return f"user{random.randint(100, 999)}"

    @staticmethod
    def password(length=12):
        chars = string.ascii_letters + string.digits + '!@#$%^&*'
        return ''.join(random.choice(chars) for _ in range(length))

    @staticmethod
    def phone_number():
        return f"+1-555-{random.randint(100, 999)}-{random.randint(1000, 9999)}"

    @staticmethod
    def street_address():
        return f"{random.randint(100, 9999)} {random.choice(['Main', 'Oak', 'Maple', 'Cedar'])} St"

    @staticmethod
    def city():
        return random.choice(['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix'])

    @staticmethod
    def state_abbr():
        return random.choice(['CA', 'NY', 'TX', 'FL', 'IL'])

    @staticmethod
    def zipcode():
        return f"{random.randint(10000, 99999)}"

    @staticmethod
    def country_code():
        return random.choice(['US', 'CA', 'UK', 'AU', 'DE'])

    @staticmethod
    def company():
        return f"{random.choice(['Tech', 'Global', 'Dynamic', 'Smart'])} {random.choice(['Solutions', 'Systems', 'Industries', 'Corp'])}"

    @staticmethod
    def company_email():
        return f"contact@{SimpleFaker.company().lower().replace(' ', '')}.com"

    @staticmethod
    def url():
        return f"https://www.{random.choice(['example', 'test', 'demo'])}.com"

    @staticmethod
    def catch_phrase():
        return f"{random.choice(['Premium', 'Ultimate', 'Professional'])} {random.choice(['Widget', 'Gadget', 'Tool'])}"

    @staticmethod
    def text(max_nb_chars=200):
        words = ['lorem', 'ipsum', 'dolor', 'sit', 'amet', 'consectetur', 'adipiscing', 'elit']
        text = ' '.join(random.choices(words, k=max_nb_chars // 6))
        return text[:max_nb_chars]

    @staticmethod
    def ean13():
        return ''.join(str(random.randint(0, 9)) for _ in range(13))

    @staticmethod
    def credit_card_number():
        return f"4{random.randint(100000000000000, 999999999999999)}"

    @staticmethod
    def credit_card_security_code():
        return f"{random.randint(100, 999)}"

    @staticmethod
    def credit_card_expire():
        month = f"{random.randint(1, 12):02d}"
        year = f"{random.randint(24, 30)}"
        return f"{month}/{year}"

    @staticmethod
    def name():
        return f"{SimpleFaker.first_name()} {SimpleFaker.last_name()}"

    @staticmethod
    def paragraphs(nb=3):
        return [SimpleFaker.text() for _ in range(nb)]


# Try to import Faker, fall back to SimpleFaker
try:
    from faker import Faker
except ImportError:
    Faker = SimpleFaker


# Example usage
if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        tdm = TestDataManager(Path(tmpdir))

        # Generate user
        user = tdm.generate_user('admin')
        print("Generated User:", json.dumps(user, indent=2))

        # Save as fixture
        tdm.save_fixture('test_admin', user)

        # Create seed data
        users = tdm.create_seed_data('user', count=5)
        print(f"\nGenerated {len(users)} users")

        # Use builder
        data = tdm.builder().with_user('admin').with_address().with_company().build()
        print("\nBuilt Data:", json.dumps(data, indent=2))

        # List fixtures
        print("\nFixtures:", tdm.list_fixtures())
