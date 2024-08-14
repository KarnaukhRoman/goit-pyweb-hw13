import asyncio
import platform

import aiohttp
import faker

NUMBER_CONTACTS = 5


def generate_fake_data(num_contacts: int):
    fake_data = faker.Faker("uk_UA")
    fake_contacts_list = []
    for _ in range(num_contacts):
        contact = {
            'first_name': fake_data.first_name(),
            'last_name': fake_data.last_name(),
            'email': fake_data.email(),
            'phone': fake_data.phone_number(),
            'birthday': fake_data.date_of_birth(minimum_age=18, maximum_age=90).isoformat(),
            'additional_info': fake_data.job()
        }
        fake_contacts_list.append(contact)
    return fake_contacts_list


async def send_contact(session, url, contact):
    async with session.post(url, json=contact) as response:
        return await response.json()

async def send_contacts_to_fastapi(contacts_list):
    url = "http://127.0.0.1:8000/contacts"  # Замініть на вашу URL
    async with aiohttp.ClientSession() as session:
        tasks = [send_contact(session, url, contact) for contact in contacts_list]
        responses = await asyncio.gather(*tasks)
        return responses

if __name__ == "__main__":
    contacts_list = generate_fake_data(NUMBER_CONTACTS)
    print(contacts_list)
    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    r = asyncio.run(send_contacts_to_fastapi(contacts_list))

