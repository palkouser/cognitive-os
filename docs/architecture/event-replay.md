# Event replay

`StreamReplayer` depends only on `EventStorePort`, the explicit event catalog, and migration
registry. It reads bounded pages in stream-version order, rejects every gap, decodes each
payload into its registered type, applies explicit migrations when requested, and calls a
generic reducer. An optional target version supports historical reconstruction.

Results report event count, first and last stream versions, and last global position. Reducer
exceptions propagate unchanged. Production aggregates, projections, snapshots, and
subscriptions are deferred.
