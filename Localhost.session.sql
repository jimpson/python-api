SELECT *
FROM rooms r
LEFT JOIN temperatures t on t.room_id = r.id;

select *
from temperatures;