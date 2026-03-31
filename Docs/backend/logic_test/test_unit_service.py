import pytest


def test_validate_listing_data_accepts_valid_listing(service, valid_listing_payload):
    service.validate_listing_data(valid_listing_payload)


@pytest.mark.parametrize('missing_field', ['price', 'latitude', 'longitude', 'source_url'])
def test_validate_listing_data_rejects_missing_required_fields(service, valid_listing_payload, missing_field):
    payload = dict(valid_listing_payload)
    payload.pop(missing_field)
    with pytest.raises(ValueError):
        service.validate_listing_data(payload)


def test_generate_fingerprint_is_stable(service):
    from dto.ListingDTO import ListingRequestDTO

    listing = ListingRequestDTO(
        title='Test', price=100.0, latitude=25.2, longitude=55.3, source_url='https://x.test'
    )
    assert service.generate_fingerprint(listing) == service.generate_fingerprint(listing)


@pytest.mark.parametrize(
    'distance,excellent,good,acceptable,expected',
    [
        (100, 400, 800, 1500, 10.0),
        (400, 400, 800, 1500, 10.0),
        (800, 400, 800, 1500, 7.0),
        (1500, 400, 800, 1500, 3.0),
        (2000, 400, 800, 1500, 0.0),
        (None, 400, 800, 1500, 0.0),
    ],
)
def test_linear_score_thresholds(service, distance, excellent, good, acceptable, expected):
    assert service.linear_score(distance, excellent, good, acceptable) == expected


def test_haversine_distance_zero_for_same_point(service):
    assert service.haversine_distance(25.2, 55.3, 25.2, 55.3) == pytest.approx(0.0, abs=0.01)



def test_find_nearest_transport_distances(service, sample_transport_points):
    result = service.find_nearest_transport_distances(25.20485, 55.27085)
    assert result['nearest_metro'] is not None
    assert result['nearest_bus'] is not None
    assert len(result['listing_transit_rows']) == 4



def test_calculate_transport_sdg_score_assigns_band_and_nearest_type(service):
    score = service.calculate_transport_sdg_score(nearest_metro_m=300, nearest_bus_m=600)
    assert score['transit_score'] > 0
    assert score['score_band'] in {'Low', 'Medium', 'High'}
    assert score['nearest_transit_type'] == 'Metro'



def test_create_listing_rejects_duplicate(service, repository, sample_transport_points, valid_listing_payload):
    first_id = service.create_listing(valid_listing_payload)
    assert first_id > 0
    with pytest.raises(ValueError, match='Duplicate listing detected'):
        service.create_listing(valid_listing_payload)
