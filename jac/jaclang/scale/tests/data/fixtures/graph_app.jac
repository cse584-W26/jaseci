"""P6 e2e fixture: a 2-hop graph (Root --> Person --> Pet) driven over HTTP.

AddPerson writes NODE_CREATE (Person, Pet) + EDGE_CREATE (root->person,
person->pet) through apply(); ListFamily is a 2-hop traversal that only
resolves if the edges and each Person's GTI blob survived the cold read
back from Postgres."""

node Person {
    has name: str;
}

node Pet {
    has name: str,
        species: str = "cat";
}

walker:pub AddPerson {
    has name: str,
        pets: list[str] = [];

    can build with Root entry {
        person = here ++> Person(name=self.name);
        for pet_name in self.pets {
            person ++> Pet(name=pet_name);
        }
        report {"person": self.name, "pets": len(self.pets)};
    }
}

walker:pub ListFamily {
    """2-hop read: Root --> Person --> Pet. Requires edges + GTI to survive."""
    can read with Root entry {
        result = [];
        for person in [-->][?:Person] {
            pets = [person -->][?:Pet];
            result.append({"name": person.name, "pets": [p.name for p in pets]});
        }
        report result;
    }
}
