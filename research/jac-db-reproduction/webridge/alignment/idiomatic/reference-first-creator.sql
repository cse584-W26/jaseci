SELECT
  CAST(JSON_UNQUOTE(JSON_EXTRACT(f.props, '$.archetype.forum_id')) AS SIGNED) AS external_forum_id,
  JSON_UNQUOTE(JSON_EXTRACT(f.props, '$.archetype.title')) AS title,
  COUNT(DISTINCT CASE WHEN memberships.friend_id = (
    SELECT hc.dst
    FROM anchors hc
    JOIN anchors author ON author.id=hc.dst
      AND author.kind='NodeAnchor' AND author.arch_type='Person'
    WHERE hc.src=p.id AND hc.kind='EdgeAnchor' AND hc.arch_type='HasCreator'
      AND (hc.dst_type IS NULL OR hc.dst_type='Person')
    ORDER BY hc.seq, hc.id
    LIMIT 1
  ) THEN p.id END) AS post_count
FROM (
  SELECT DISTINCT member.src AS forum_id, member.dst AS friend_id
  FROM anchors member
  JOIN (
    SELECT k.dst AS id FROM anchors k
    WHERE k.src=? AND k.kind='EdgeAnchor' AND k.arch_type='Knows'
      AND (k.dst_type IS NULL OR k.dst_type='Person')
    UNION
    SELECT k.src AS id FROM anchors k
    WHERE k.dst=? AND k.kind='EdgeAnchor' AND k.arch_type='Knows'
      AND (k.src_type IS NULL OR k.src_type='Person')
  ) friends ON friends.id=member.dst
  JOIN anchors friend ON friend.id=friends.id
    AND friend.kind='NodeAnchor' AND friend.arch_type='Person'
  WHERE member.kind='EdgeAnchor' AND member.arch_type='HasMember'
    AND (member.src_type IS NULL OR member.src_type='Forum')
    AND CAST(JSON_UNQUOTE(JSON_EXTRACT(member.props, '$.archetype.joinDate')) AS SIGNED)>?
) memberships
JOIN anchors f ON f.id=memberships.forum_id
  AND f.kind='NodeAnchor' AND f.arch_type='Forum'
LEFT JOIN anchors co ON co.src=f.id
  AND co.kind='EdgeAnchor' AND co.arch_type='ContainerOf'
  AND (co.dst_type IS NULL OR co.dst_type='Post')
LEFT JOIN anchors p ON p.id=co.dst
  AND p.kind='NodeAnchor' AND p.arch_type='Post'
GROUP BY f.id, external_forum_id, title
ORDER BY post_count DESC, external_forum_id ASC
LIMIT 20
