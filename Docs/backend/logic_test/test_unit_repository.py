from dto.ListingDTO import ListingRequestDTO


def test_transport_point_insert_and_count(repository):
    repository.insert_transport_point('Metro A', 'Metro', 25.2048, 55.2708, 'M1')
    repository.insert_transport_point('Bus A', 'Bus', 25.2058, 55.2718, 'B1')
    assert repository.count_transport_points() == 2



def test_insert_and_fetch_listing(repository):
    listing = ListingRequestDTO(
        title='Repo Test Listing',
        price=900000,
        bedrooms=1,
        bathrooms=1,
        area_sqft=700,
        latitude=25.21,
        longitude=55.28,
        source_url='https://example.com/repo-test',
        source_site='Bayut',
        realtor_name='Repo Agent',
        realtor_contact='0501111111',
    )
    listing_id = repository.insert_listing(listing, 'repo-fingerprint')
    repository.upsert_sustainability_score(
        listing_id=listing_id,
        transit_score=8.5,
        distance_to_nearest_transit=120.0,
        nearest_transit_type='Metro',
        inclusivity_rank=0,
        accessibility_features=0,
        final_score=8.5,
        score_band='High',
    )

    all_listings = repository.get_all_listings()
    fetched = repository.get_listing_by_id(listing_id)

    assert len(all_listings) == 1
    assert all_listings[0].title == 'Repo Test Listing'
    assert fetched is not None
    assert fetched.listing_id == listing_id
    assert fetched.final_score == 8.5
    assert fetched.dist_transit == 120.0
