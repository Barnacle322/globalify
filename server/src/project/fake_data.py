from faker import Faker

fake = Faker()


def get_names(amount: int):
    names = [fake.first_name() for _ in range(amount)]
    return names


def get_last_names(amount: int):
    last_names = [fake.last_name() for _ in range(amount)]
    return last_names


def get_companies(amount: int):
    companies = [fake.company() for _ in range(amount)]
    return companies


def get_job_positions(amount: int):
    job_positions = [fake.job() for _ in range(amount)]
    return job_positions


def get_emails(amount: int):
    emails = [fake.email() for _ in range(amount)]
    return emails


def get_websites(amount: int):
    websites = [fake.uri() for _ in range(amount)]
    return websites
