CREATE TABLE knows(person1_id BIGINT NOT NULL,person2_id BIGINT NOT NULL,PRIMARY KEY(person1_id,person2_id));
CREATE TABLE forum(id BIGINT PRIMARY KEY,title TEXT CHARACTER SET utf8mb4 NOT NULL);
CREATE TABLE forum_member(forum_id BIGINT NOT NULL,person_id BIGINT NOT NULL,join_date BIGINT NOT NULL,PRIMARY KEY(forum_id,person_id),KEY member_person(person_id));
CREATE TABLE post(id BIGINT PRIMARY KEY,creator_id BIGINT NOT NULL,forum_id BIGINT NOT NULL,KEY post_forum(forum_id),KEY post_creator(creator_id));
