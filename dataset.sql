DROP TABLE IF EXISTS student_performance;

CREATE TABLE student_performance (
    school VARCHAR(20),
    sex VARCHAR(10),
    age INT,
    address VARCHAR(20),
    Pstatus VARCHAR(20),
    Medu INT,
    Fedu INT,
    Mjob VARCHAR(50),
    Fjob VARCHAR(50),
    reason VARCHAR(50),
    guardian VARCHAR(50),
    traveltime INT,
    studytime INT,
    failures INT,
    schoolsup VARCHAR(10),
    famsup VARCHAR(10),
    paid VARCHAR(10),
    activities VARCHAR(10),
    nursery VARCHAR(10),
    higher VARCHAR(10),
    internet VARCHAR(10),
    romantic VARCHAR(10),
    famrel INT,
    freetime INT,
    goout INT,
    Dalc INT,
    Walc INT,
    health INT,
    absences INT,
    G1 INT,
    G2 INT,
    G3 INT
);

select * from student_performance;