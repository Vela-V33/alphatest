#!/usr/bin/env python3
"""
Form Intelligence Module
Automatically detects and intelligently fills form fields.
"""

from typing import Dict, List, Optional, Any, Callable
from playwright.async_api import Page, Locator
import re


class FormField:
    """Represents a detected form field."""

    def __init__(
        self,
        element: Locator,
        field_type: str,
        label: str = "",
        placeholder: str = "",
        name: str = "",
        required: bool = False
    ):
        self.element = element
        self.field_type = field_type  # text, email, password, select, checkbox, etc.
        self.label = label
        self.placeholder = placeholder
        self.name = name
        self.required = required

    def to_dict(self) -> Dict:
        return {
            'type': self.field_type,
            'label': self.label,
            'placeholder': self.placeholder,
            'name': self.name,
            'required': self.required
        }


class FormIntelligence:
    """Intelligent form detection and filling."""

    def __init__(self, page: Page, status_callback: Callable = None):
        self.page = page
        self.status = status_callback or print

        # Field type patterns
        self.field_patterns = {
            'email': [
                r'email',
                r'e-mail',
                r'mail',
                r'user.*mail'
            ],
            'password': [
                r'password',
                r'passwd',
                r'pwd'
            ],
            'username': [
                r'username',
                r'user.*name',
                r'login',
                r'account'
            ],
            'first_name': [
                r'first.*name',
                r'fname',
                r'given.*name'
            ],
            'last_name': [
                r'last.*name',
                r'lname',
                r'surname',
                r'family.*name'
            ],
            'phone': [
                r'phone',
                r'telephone',
                r'mobile',
                r'cell'
            ],
            'address': [
                r'address',
                r'street',
                r'addr'
            ],
            'city': [
                r'city',
                r'town'
            ],
            'state': [
                r'state',
                r'province',
                r'region'
            ],
            'zip': [
                r'zip',
                r'postal',
                r'postcode'
            ],
            'country': [
                r'country',
                r'nation'
            ],
            'company': [
                r'company',
                r'organization',
                r'employer'
            ],
            'website': [
                r'website',
                r'url',
                r'site'
            ],
            'search': [
                r'search',
                r'query',
                r'find'
            ]
        }

    async def detect_forms(self) -> List[Dict]:
        """Detect all forms on the page."""
        self.status("   [Form Detection] Scanning page for forms...")

        try:
            forms = await self.page.locator('form').all()

            detected_forms = []

            for i, form in enumerate(forms):
                form_data = {
                    'index': i,
                    'fields': [],
                    'submit_button': None
                }

                # Detect fields in this form
                fields = await self._detect_form_fields(form)
                form_data['fields'] = fields

                # Detect submit button
                submit = await self._find_submit_button(form)
                form_data['submit_button'] = submit

                detected_forms.append(form_data)

            self.status(f"   [Form Detection] Found {len(detected_forms)} forms")

            return detected_forms

        except Exception as e:
            self.status(f"   [Form Detection] Error: {str(e)[:100]}")
            return []

    async def _detect_form_fields(self, form: Locator) -> List[Dict]:
        """Detect fields within a form."""
        fields = []

        # Get all input elements
        inputs = await form.locator('input').all()

        for input_elem in inputs:
            try:
                input_type = await input_elem.get_attribute('type') or 'text'
                name = await input_elem.get_attribute('name') or ''
                placeholder = await input_elem.get_attribute('placeholder') or ''
                required = await input_elem.get_attribute('required') is not None

                # Try to find associated label
                label = await self._find_label_for_input(input_elem)

                # Infer field purpose
                purpose = self._infer_field_purpose(name, placeholder, label, input_type)

                fields.append({
                    'type': input_type,
                    'name': name,
                    'placeholder': placeholder,
                    'label': label,
                    'required': required,
                    'purpose': purpose
                })

            except Exception:
                continue

        # Get select elements
        selects = await form.locator('select').all()

        for select_elem in selects:
            try:
                name = await select_elem.get_attribute('name') or ''
                required = await select_elem.get_attribute('required') is not None
                label = await self._find_label_for_input(select_elem)

                purpose = self._infer_field_purpose(name, '', label, 'select')

                fields.append({
                    'type': 'select',
                    'name': name,
                    'label': label,
                    'required': required,
                    'purpose': purpose
                })

            except Exception:
                continue

        # Get textarea elements
        textareas = await form.locator('textarea').all()

        for textarea_elem in textareas:
            try:
                name = await textarea_elem.get_attribute('name') or ''
                placeholder = await textarea_elem.get_attribute('placeholder') or ''
                required = await textarea_elem.get_attribute('required') is not None
                label = await self._find_label_for_input(textarea_elem)

                purpose = self._infer_field_purpose(name, placeholder, label, 'textarea')

                fields.append({
                    'type': 'textarea',
                    'name': name,
                    'placeholder': placeholder,
                    'label': label,
                    'required': required,
                    'purpose': purpose
                })

            except Exception:
                continue

        return fields

    async def _find_label_for_input(self, input_elem: Locator) -> str:
        """Find the label associated with an input element."""
        try:
            # Try to find by 'for' attribute
            input_id = await input_elem.get_attribute('id')
            if input_id:
                label = await self.page.locator(f'label[for="{input_id}"]').first.text_content()
                if label:
                    return label.strip()

            # Try to find parent label
            parent_label = input_elem.locator('xpath=ancestor::label[1]')
            if await parent_label.count() > 0:
                label = await parent_label.text_content()
                if label:
                    return label.strip()

            # Try aria-label
            aria_label = await input_elem.get_attribute('aria-label')
            if aria_label:
                return aria_label

        except Exception:
            pass

        return ""

    def _infer_field_purpose(
        self,
        name: str,
        placeholder: str,
        label: str,
        field_type: str
    ) -> str:
        """Infer the purpose of a field from its attributes."""

        # Combine all text for pattern matching
        combined = f"{name} {placeholder} {label}".lower()

        # Check field type first
        if field_type == 'email':
            return 'email'
        elif field_type == 'password':
            return 'password'
        elif field_type == 'tel':
            return 'phone'
        elif field_type == 'url':
            return 'website'
        elif field_type == 'search':
            return 'search'

        # Check against patterns
        for purpose, patterns in self.field_patterns.items():
            for pattern in patterns:
                if re.search(pattern, combined, re.IGNORECASE):
                    return purpose

        # Default to generic text
        if field_type == 'textarea':
            return 'message'
        elif field_type == 'select':
            return 'selection'
        else:
            return 'text'

    async def _find_submit_button(self, form: Locator) -> Optional[str]:
        """Find the submit button in a form."""
        try:
            # Try input[type="submit"]
            submit = form.locator('input[type="submit"], button[type="submit"]').first
            if await submit.count() > 0:
                value = await submit.get_attribute('value') or await submit.text_content()
                return value or 'Submit'

            # Try buttons with common text
            common_submits = ['submit', 'send', 'login', 'sign in', 'register', 'continue']
            for text in common_submits:
                button = form.locator(f'button:has-text("{text}")').first
                if await button.count() > 0:
                    return text.title()

            # Try any button in the form
            any_button = form.locator('button').first
            if await any_button.count() > 0:
                text = await any_button.text_content()
                return text.strip() if text else 'Submit'

        except Exception:
            pass

        return None

    async def auto_fill_form(
        self,
        form_index: int = 0,
        field_values: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """
        Automatically fill a detected form.

        Args:
            form_index: Index of the form to fill (0 = first form)
            field_values: Dict mapping field purposes to values

        Returns:
            Dict with success status and filled fields
        """
        self.status(f"   [Auto Fill] Filling form {form_index}...")

        if field_values is None:
            field_values = {}

        try:
            forms = await self.page.locator('form').all()

            if form_index >= len(forms):
                return {
                    'success': False,
                    'error': f'Form {form_index} not found'
                }

            form = forms[form_index]
            fields = await self._detect_form_fields(form)

            filled_fields = []

            for field in fields:
                purpose = field['purpose']

                # Check if we have a value for this field purpose
                if purpose in field_values:
                    value = field_values[purpose]

                    # Find the input element
                    if field['name']:
                        input_elem = form.locator(f'[name="{field["name"]}"]').first
                    elif field['placeholder']:
                        input_elem = form.locator(f'[placeholder="{field["placeholder"]}"]').first
                    else:
                        continue

                    # Fill the field
                    if await input_elem.count() > 0:
                        await input_elem.fill(value)
                        filled_fields.append({
                            'purpose': purpose,
                            'name': field['name'],
                            'value': value
                        })
                        self.status(f"   [Auto Fill] Filled {purpose}: {field['name']}")

            return {
                'success': True,
                'form_index': form_index,
                'filled_fields': filled_fields,
                'total_filled': len(filled_fields)
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def get_default_values(self, purpose: str) -> Optional[str]:
        """Get default test values for common field purposes."""
        defaults = {
            'email': 'test@example.com',
            'password': 'TestPassword123!',
            'username': 'testuser',
            'first_name': 'John',
            'last_name': 'Doe',
            'phone': '555-0123',
            'address': '123 Test Street',
            'city': 'Test City',
            'state': 'CA',
            'zip': '12345',
            'country': 'United States',
            'company': 'Test Company',
            'website': 'https://example.com',
            'search': 'test query',
            'message': 'This is a test message.'
        }

        return defaults.get(purpose)
