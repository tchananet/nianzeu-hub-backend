def profile_payload():
    return dict(
        display_name="Ada", headline="Software developer", bio="", city="Douala",
        country_code="CM", availability="freelance", experience_level="senior", rate=None,
        skill_ids=["00000000-0000-4000-8000-000000000001"],
        experiences=[dict(title="Developer", organization="Example", description="",
                          start_date="2020-01-01", end_date=None)],
        certifications=[dict(name="Certificate", issuer="Example", issued_on="2020-01-01",
                             expires_on=None, credential_url=None)],
        contacts=dict(email="private@example.com", phone="+237699000000", whatsapp=None,
                      email_visible=False, phone_visible=True, whatsapp_visible=False),
    )
