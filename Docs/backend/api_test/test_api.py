def test_health_check(client):
    response = client.get('/api/health')
    assert response.status_code == 200
    assert response.get_json()['status'] == 'ok'



def test_create_and_fetch_listing_flow(client, app_with_test_db, valid_listing_payload):
    _, repo, _ = app_with_test_db
    repo.insert_transport_point('Metro A', 'Metro', 25.2048, 55.2708, 'M1')
    repo.insert_transport_point('Bus A', 'Bus', 25.2058, 55.2708, 'B1')

    create_response = client.post('/api/listings', json=valid_listing_payload)
    assert create_response.status_code == 201
    listing_id = create_response.get_json()['listingId']

    list_response = client.get('/api/listings')
    assert list_response.status_code == 200
    assert len(list_response.get_json()) == 1

    detail_response = client.get(f'/api/listings/{listing_id}')
    assert detail_response.status_code == 200
    body = detail_response.get_json()
    assert body['listingId'] == listing_id
    assert body['title'] == valid_listing_payload['title']
    assert body['finalScore'] is not None



def test_create_listing_rejects_invalid_json_body(client):
    response = client.post('/api/listings', data='not-json', content_type='text/plain')
    assert response.status_code in (400, 415, 500)



def test_create_listing_rejects_missing_required_field(client, valid_listing_payload):
    payload = dict(valid_listing_payload)
    payload.pop('price')
    response = client.post('/api/listings', json=payload)
    assert response.status_code == 400



def test_create_listing_rejects_duplicate(client, app_with_test_db, valid_listing_payload):
    _, repo, _ = app_with_test_db
    repo.insert_transport_point('Metro A', 'Metro', 25.2048, 55.2708, 'M1')
    repo.insert_transport_point('Bus A', 'Bus', 25.2058, 55.2708, 'B1')

    first = client.post('/api/listings', json=valid_listing_payload)
    second = client.post('/api/listings', json=valid_listing_payload)
    assert first.status_code == 201
    assert second.status_code == 400
