"""
Seed script - populates the database with demo faculty data.
Run this once: python seed.py
"""

import secrets
from app import app, init_db, get_db
from werkzeug.security import generate_password_hash

def seed():
    with app.app_context():
        init_db()
        db = get_db()

        # Check if data already exists
        if db.execute('SELECT COUNT(*) c FROM faculty').fetchone()['c'] > 0:
            print("Database already has data. Skipping seed.")
            return

        # Create demo faculty members
        faculty_data = [
            {
                'email': 'anand.kumar@university.edu',
                'username': 'anand',
                'password': 'anand123',
                'full_name': 'Dr. Anand Kumar',
                'designation': 'Associate Professor',
                'department': 'Computer Science and Engineering',
                'institution': 'National Institute of Technology',
                'phone': '+91-9876543210',
                'office_location': 'Block A, Room 305',
                'office_hours': 'Mon-Fri, 2:00 PM - 4:00 PM',
                'visiting_hours': 'Mon-Wed, 10:00 AM - 12:00 PM',
                'address': 'Department of CSE, NIT Campus, Jaipur, Rajasthan - 302017',
                'bio': 'Dr. Anand Kumar is an Associate Professor in the Department of Computer Science and Engineering at NIT Jaipur. He received his Ph.D. from IIT Delhi in 2015 and has over 12 years of teaching and research experience. His work focuses on machine learning, natural language processing, and distributed systems. He has published over 45 papers in peer-reviewed journals and conferences, and has supervised 8 Ph.D. students to completion. He currently leads the Intelligent Systems Lab and serves as the faculty advisor for the ACM student chapter.',
                'website': 'https://anandkumar.nitj.ac.in',
                'google_scholar': 'https://scholar.google.com/citations?user=anandkumar',
                'linkedin': 'https://linkedin.com/in/anandkumar',
                'github': 'https://github.com/anandkumar',
                'research_summary': 'Machine Learning, Natural Language Processing, Distributed Computing, Data Mining',
            },
            {
                'email': 'sunita.reddy@university.edu',
                'username': 'sunita',
                'password': 'sunita123',
                'full_name': 'Dr. Sunita Reddy',
                'designation': 'Professor',
                'department': 'Electronics and Communication Engineering',
                'institution': 'National Institute of Technology',
                'phone': '+91-9876543211',
                'office_location': 'Block B, Room 210',
                'office_hours': 'Tue-Thu, 11:00 AM - 1:00 PM',
                'visiting_hours': 'Mon-Fri, 3:00 PM - 5:00 PM',
                'address': 'Department of ECE, NIT Campus, Jaipur, Rajasthan - 302017',
                'bio': 'Dr. Sunita Reddy is a Professor in the Department of Electronics and Communication Engineering at NIT Jaipur. She earned her Ph.D. from IISc Bangalore in 2010 and has over 15 years of academic experience. Her research areas include VLSI design, embedded systems, IoT, and signal processing. She has authored 2 textbooks, holds 3 patents, and has published over 60 research papers. She has received the Best Paper Award at IEEE INDICON 2022 and serves on the editorial board of the Journal of Signal Processing Systems.',
                'website': 'https://sunitareddy.nitj.ac.in',
                'google_scholar': 'https://scholar.google.com/citations?user=sunitareddy',
                'linkedin': 'https://linkedin.com/in/sunitareddy',
                'github': '',
                'research_summary': 'VLSI Design, Embedded Systems, Internet of Things, Digital Signal Processing',
            },
        ]

        for f in faculty_data:
            # Create faculty account
            db.execute(
                'INSERT INTO faculty (email, password_hash, full_name, username, designation, department, institution, phone, office_location, office_hours, visiting_hours, address, bio, website, google_scholar, linkedin, github, research_summary) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                (f['email'], generate_password_hash(f['password']), f['full_name'], f['username'],
                 f['designation'], f['department'], f['institution'], f['phone'],
                 f['office_location'], f['office_hours'], f['visiting_hours'], f['address'],
                 f['bio'], f['website'], f['google_scholar'], f['linkedin'],
                 f['github'], f['research_summary'])
            )
            fid = db.execute('SELECT last_insert_rowid()').fetchone()[0]

            if f['username'] == 'anand':
                # Qualifications
                quals = [
                    ('Ph.D. Computer Science', 'Machine Learning', 'Indian Institute of Technology Delhi', '2015'),
                    ('M.Tech Computer Science', 'Artificial Intelligence', 'Indian Institute of Technology Kanpur', '2010'),
                    ('B.Tech Computer Engineering', 'Computer Science', 'Rajasthan Technical University', '2008'),
                ]
                cert_photos = ['phd_certificate.svg', '', '']
                for i, (degree, spec, uni, year) in enumerate(quals):
                    db.execute(
                        'INSERT INTO qualifications (faculty_id, degree, specialization, university, year_of_passing, certificate_photo) VALUES (?,?,?,?,?,?)',
                        (fid, degree, spec, uni, year, cert_photos[i])
                    )

                # Research interests
                research = [
                    ('Machine Learning and Deep Learning', 'Research on supervised and unsupervised learning algorithms, including neural network architectures for classification and regression tasks.'),
                    ('Natural Language Processing', 'Computational linguistics, sentiment analysis, text classification, and language modeling using transformer architectures.'),
                    ('Distributed Systems', 'Cloud computing, microservices architecture, and scalable distributed computing frameworks.'),
                    ('Data Mining and Analytics', 'Pattern recognition in large datasets, knowledge discovery, and predictive analytics.'),
                ]
                for title, desc in research:
                    db.execute(
                        'INSERT INTO research_interests (faculty_id, title, description) VALUES (?,?,?)',
                        (fid, title, desc)
                    )

                # Achievements
                achievements = [
                    ('Best Paper Award - ICML 2022', 'Received Best Paper Award for "Efficient Transformer Architectures for Low-Resource NLP" at the International Conference on Machine Learning.', 'award', '2022'),
                    ('INSA Young Scientist Award', 'Awarded by the Indian National Science Academy for outstanding contributions to computational linguistics.', 'award', '2019'),
                    ('Oracle ACE Award 2023', 'Recognized by Oracle Corporation for contributions to cloud-native application development.', 'recognition', '2023'),
                    ('DST Early Career Research Award', 'Department of Science and Technology grant for research in federated learning systems.', 'grant', '2017'),
                    ('Fellowship - Indian Society for Technical Education', 'Elected Fellow of ISTE for significant contributions to engineering education.', 'fellowship', '2021'),
                    ('Google Research Award', 'Collaborative research grant for work on multilingual NLP systems.', 'grant', '2020'),
                ]
                ach_certs = ['best_paper_award.svg', '', 'aws_certificate.svg', '', '', '']
                for i, (title, desc, cat, year) in enumerate(achievements):
                    db.execute(
                        'INSERT INTO achievements (faculty_id, title, description, category, year, certificate_photo) VALUES (?,?,?,?,?,?)',
                        (fid, title, desc, cat, year, ach_certs[i])
                    )

                # Publications
                pubs = [
                    ('Efficient Transformer Architectures for Low-Resource NLP', 'A. Kumar, R. Singh, P. Sharma', 'Proceedings of ICML', '2022', '10.1109/icml.2022.12345', 'https://doi.org/10.1109/icml.2022.12345', 'We propose a novel transformer architecture that achieves comparable performance to large language models while using 60% fewer parameters. Our approach leverages adaptive attention mechanisms and sparse connectivity patterns to reduce computational overhead while maintaining accuracy on standard NLP benchmarks.', 'conference'),
                    ('Deep Learning Approaches for Sentiment Analysis in Hindi Text', 'A. Kumar, M. Gupta', 'Journal of Natural Language Processing', '2021', '10.1016/j.nlp.2021.67890', 'https://doi.org/10.1016/j.nlp.2021.67890', 'This paper presents a comprehensive study of deep learning methods for sentiment analysis in Hindi, a low-resource language. We introduce a new annotated dataset and demonstrate that transfer learning from English models with language-adaptive fine-tuning achieves state-of-the-art results.', 'journal'),
                    ('Federated Learning for Privacy-Preserving Medical Data Analysis', 'A. Kumar, S. Patel, K. Venkatesh', 'IEEE Transactions on Medical Imaging', '2020', '10.1109/tmi.2020.30123', 'https://doi.org/10.1109/tmi.2020.30123', 'We present a federated learning framework that enables collaborative training of medical imaging models across multiple hospitals without sharing raw patient data. Our method achieves 95% of the centralized model accuracy while providing formal differential privacy guarantees.', 'journal'),
                    ('Scalable Microservices Architecture for Real-Time Data Processing', 'A. Kumar, V. Mehta', 'ACM Computing Surveys', '2019', '10.1145/3312345', 'https://doi.org/10.1145/3312345', 'A comprehensive survey of microservices architectures for real-time data processing systems. We analyze 25 production deployments and propose a reference architecture pattern that addresses common challenges in scalability, fault tolerance, and data consistency.', 'journal'),
                ]
                for title, authors, journal, year, doi, url, abstract, ptype in pubs:
                    db.execute(
                        'INSERT INTO publications (faculty_id, title, authors, journal, year, doi, url, abstract, pub_type) VALUES (?,?,?,?,?,?,?,?,?)',
                        (fid, title, authors, journal, year, doi, url, abstract, ptype)
                    )

                # Courses
                courses = [
                    ('Machine Learning', 'CS401', 'Introduction to machine learning algorithms, supervised and unsupervised learning, neural networks, evaluation metrics, and practical implementation using Python and scikit-learn.', 'Odd Semester 2024-25', 'Mon-Wed 10:00-11:30 AM'),
                    ('Natural Language Processing', 'CS502', 'Advanced course covering text processing, language modeling, named entity recognition, sentiment analysis, and modern transformer-based approaches to NLP.', 'Even Semester 2024-25', 'Tue-Thu 2:00-3:30 PM'),
                    ('Data Structures and Algorithms', 'CS201', 'Fundamental data structures including arrays, linked lists, trees, graphs, and hash tables. Algorithm analysis, sorting, searching, and graph algorithms.', 'Odd Semester 2024-25', 'Mon-Fri 9:00-10:00 AM'),
                ]
                for name, code, desc, sem, sched in courses:
                    db.execute(
                        'INSERT INTO courses (faculty_id, name, code, description, semester, schedule) VALUES (?,?,?,?,?,?)',
                        (fid, name, code, desc, sem, sched)
                    )

                # Students
                students = [
                    ('Rahul Sharma', 'Ph.D.', 'Deep Learning for Medical Image Segmentation', 'ongoing', '2021', 'rahul.sharma@nitj.ac.in'),
                    ('Priya Singh', 'Ph.D.', 'Federated Learning Systems', 'ongoing', '2022', 'priya.singh@nitj.ac.in'),
                    ('Amit Verma', 'M.Tech', 'Sentiment Analysis in Multilingual Settings', 'completed', '2020', 'amit.verma@nitj.ac.in'),
                    ('Neha Gupta', 'Ph.D.', 'Distributed Computing Frameworks', 'ongoing', '2023', 'neha.gupta@nitj.ac.in'),
                    ('Vikram Joshi', 'M.Tech', 'Microservices Architecture Patterns', 'completed', '2021', 'vikram.joshi@nitj.ac.in'),
                ]
                for name, prog, topic, status, year, email in students:
                    db.execute(
                        'INSERT INTO students (faculty_id, name, program, research_topic, status, start_year, email) VALUES (?,?,?,?,?,?,?)',
                        (fid, name, prog, topic, status, year, email)
                    )

                # Projects
                projects = [
                    ('Federated Learning for Healthcare', 'Developing a privacy-preserving federated learning platform for collaborative medical research across multiple hospitals in India.', 'DST-SERB', '25,00,000', 'ongoing', '2022', ''),
                    ('Multilingual NLP Toolkit', 'Building an open-source toolkit for NLP tasks in 12 Indian languages with pre-trained models and fine-tuning utilities.', 'MeitY', '18,00,000', 'ongoing', '2023', ''),
                    ('Smart Campus IoT Network', 'Design and deployment of an IoT-based smart campus monitoring system for energy management and security.', 'DPRP', '12,50,000', 'completed', '2020', '2023'),
                ]
                for title, desc, agency, amt, status, sy, ey in projects:
                    db.execute(
                        'INSERT INTO projects (faculty_id, title, description, funding_agency, amount, status, start_year, end_year) VALUES (?,?,?,?,?,?,?,?)',
                        (fid, title, desc, agency, amt, status, sy, ey)
                    )

                # Announcements
                announcements = [
                    ('PhD Openings for Spring 2025', 'I have openings for 2 Ph.D. students in the areas of Federated Learning and NLP. Interested candidates with a strong background in machine learning and programming should send their CV and research statement.', 1),
                    ('Guest Lecture on Large Language Models', 'A guest lecture on "The Future of Large Language Models" will be held on September 15, 2024, in Auditorium A. All students and faculty are welcome.', 0),
                    ('Lab Meeting Schedule Updated', 'Weekly lab meetings for the Intelligent Systems Lab will now be held every Friday at 4:00 PM in Room 305. All group members must attend.', 0),
                ]
                for title, content, important in announcements:
                    db.execute(
                        'INSERT INTO announcements (faculty_id, title, content, is_important) VALUES (?,?,?,?)',
                        (fid, title, content, important)
                    )

            elif f['username'] == 'sunita':
                # Qualifications
                quals = [
                    ('Ph.D. Electronics and Communication', 'VLSI Design', 'Indian Institute of Science Bangalore', '2010'),
                    ('M.Tech VLSI Systems', 'VLSI Design', 'National Institute of Technology Trichy', '2006'),
                    ('B.E. Electronics and Communication', 'Electronics', 'Visvesvaraya Technological University', '2004'),
                ]
                cert_photos = ['phd_sunita.svg', '', '']
                for i, (degree, spec, uni, year) in enumerate(quals):
                    db.execute(
                        'INSERT INTO qualifications (faculty_id, degree, specialization, university, year_of_passing, certificate_photo) VALUES (?,?,?,?,?,?)',
                        (fid, degree, spec, uni, year, cert_photos[i])
                    )

                # Research interests
                research = [
                    ('VLSI Design and Verification', 'Low-power VLSI circuit design, hardware description languages, and formal verification techniques for complex digital systems.'),
                    ('Internet of Things', 'IoT system architecture, sensor networks, edge computing, and smart infrastructure development.'),
                    ('Digital Signal Processing', 'Audio and image signal processing, adaptive filtering, and real-time DSP system implementation on FPGAs.'),
                    ('Embedded Systems', 'Real-time operating systems, ARM architecture, and embedded system design for industrial applications.'),
                ]
                for title, desc in research:
                    db.execute(
                        'INSERT INTO research_interests (faculty_id, title, description) VALUES (?,?,?)',
                        (fid, title, desc)
                    )

                # Achievements
                achievements = [
                    ('IEEE INDICON 2022 Best Paper Award', 'Best paper award for "Low-Power FPGA Implementation of Adaptive Signal Processing Algorithms" at IEEE INDICON.', 'award', '2022'),
                    ('INAE Young Engineer Award', 'Indian National Academy of Engineering award for contributions to VLSI design methodology.', 'award', '2018'),
                    ('Patent - Smart Sensor Array', 'Granted Indian patent for "Array-based sensor system for real-time environmental monitoring" (IN202141056789).', 'patent', '2021'),
                    ('Patent - Low-Power Memory Controller', 'Patent granted for "Energy-efficient memory controller for IoT devices" (IN202041023456).', 'patent', '2020'),
                    ('DST-Women Scientist Award', 'Recognized for research contributions in embedded systems for healthcare applications.', 'award', '2019'),
                    ('Editorial Board - Journal of Signal Processing Systems', 'Appointed to the editorial board of the Springer Journal of Signal Processing Systems.', 'recognition', '2023'),
                ]
                ach_certs = ['best_paper_sunita.svg', '', '', '', '', 'ieee_fellow.svg']
                for i, (title, desc, cat, year) in enumerate(achievements):
                    db.execute(
                        'INSERT INTO achievements (faculty_id, title, description, category, year, certificate_photo) VALUES (?,?,?,?,?,?)',
                        (fid, title, desc, cat, year, ach_certs[i])
                    )

                # Publications
                pubs = [
                    ('Low-Power FPGA Implementation of Adaptive Signal Processing Algorithms', 'S. Reddy, K. Raman, A. Nair', 'IEEE INDICON Proceedings', '2022', '10.1109/indicon.2022.98765', 'https://doi.org/10.1109/indicon.2022.98765', 'This paper presents an optimized FPGA implementation of LMS-based adaptive filtering algorithms targeting low-power IoT applications. Our implementation achieves 40% power reduction compared to existing solutions while maintaining signal processing accuracy.', 'conference'),
                    ('Energy-Efficient Memory Architecture for IoT Edge Devices', 'S. Reddy, P. Menon', 'IEEE Transactions on VLSI Systems', '2021', '10.1109/tvlsi.2021.56789', 'https://doi.org/10.1109/tvlsi.2021.56789', 'We propose a novel memory architecture that reduces static power consumption in IoT edge devices by 35% through intelligent power gating and adaptive refresh scheduling. The architecture is validated on a 28nm test chip.', 'journal'),
                    ('IoT-Based Smart Healthcare Monitoring System: A Comprehensive Survey', 'S. Reddy, R. Das, M. Joshi', 'ACM Computing Surveys', '2020', '10.1145/3456789', 'https://doi.org/10.1145/3456789', 'A comprehensive survey of IoT-based healthcare monitoring systems covering sensor technologies, communication protocols, data processing frameworks, and privacy considerations. We analyze 40 recent systems and propose a reference architecture.', 'journal'),
                ]
                for title, authors, journal, year, doi, url, abstract, ptype in pubs:
                    db.execute(
                        'INSERT INTO publications (faculty_id, title, authors, journal, year, doi, url, abstract, pub_type) VALUES (?,?,?,?,?,?,?,?,?)',
                        (fid, title, authors, journal, year, doi, url, abstract, ptype)
                    )

                # Courses
                courses = [
                    ('VLSI Design', 'EC401', 'CMOS circuit design, logic synthesis, physical design, timing analysis, and FPGA-based prototyping. Hands-on projects using Cadence and Xilinx tools.', 'Odd Semester 2024-25', 'Mon-Wed 11:00 AM-12:30 PM'),
                    ('Digital Signal Processing', 'EC301', 'Discrete-time signals and systems, Z-transform, DFT, FFT, FIR and IIR filter design, and practical DSP implementation.', 'Even Semester 2024-25', 'Tue-Thu 10:00-11:30 AM'),
                    ('Embedded Systems', 'EC501', 'ARM Cortex-M architecture, RTOS concepts, interrupt handling, peripheral interfacing, and real-time system design with FreeRTOS.', 'Odd Semester 2024-25', 'Mon-Fri 2:00-3:00 PM'),
                ]
                for name, code, desc, sem, sched in courses:
                    db.execute(
                        'INSERT INTO courses (faculty_id, name, code, description, semester, schedule) VALUES (?,?,?,?,?,?)',
                        (fid, name, code, desc, sem, sched)
                    )

                # Students
                students = [
                    ('Deepak Nair', 'Ph.D.', 'Low-Power IoT Circuit Design', 'ongoing', '2021', 'deepak.nair@nitj.ac.in'),
                    ('Anjali Menon', 'Ph.D.', 'Smart Sensor Networks for Agriculture', 'ongoing', '2022', 'anjali.menon@nitj.ac.in'),
                    ('Suresh Pillai', 'M.Tech', 'FPGA-Based Signal Processing', 'completed', '2020', 'suresh.pillai@nitj.ac.in'),
                    ('Kavitha R.', 'Ph.D.', 'Embedded Systems for Healthcare', 'ongoing', '2023', 'kavitha.r@nitj.ac.in'),
                ]
                for name, prog, topic, status, year, email in students:
                    db.execute(
                        'INSERT INTO students (faculty_id, name, program, research_topic, status, start_year, email) VALUES (?,?,?,?,?,?,?)',
                        (fid, name, prog, topic, status, year, email)
                    )

                # Projects
                projects = [
                    ('Smart Agriculture IoT Platform', 'Designing an IoT-based precision agriculture system with soil sensors, weather stations, and automated irrigation control using LoRaWAN connectivity.', 'DST-Agri', '32,00,000', 'ongoing', '2023', ''),
                    ('Low-Power Wearable Health Monitor', 'Developing a wearable health monitoring device with ECG, SpO2, and temperature sensors using ultra-low-power microcontrollers.', 'DBT', '20,00,000', 'ongoing', '2022', ''),
                    ('FPGA Signal Processing Library', 'An open-source library of optimized signal processing IP cores for Xilinx and Intel FPGAs.', 'MeitY', '8,00,000', 'completed', '2019', '2022'),
                ]
                for title, desc, agency, amt, status, sy, ey in projects:
                    db.execute(
                        'INSERT INTO projects (faculty_id, title, description, funding_agency, amount, status, start_year, end_year) VALUES (?,?,?,?,?,?,?,?)',
                        (fid, title, desc, agency, amt, status, sy, ey)
                    )

                # Announcements
                announcements = [
                    ('VLSI Design Lab - New Equipment', 'The VLSI Design Lab has received new Xilinx Artix-7 FPGA boards for student projects. Slots are available for final year projects - contact me during office hours.', 1),
                    ('Workshop on Embedded Systems with FreeRTOS', 'A 3-day hands-on workshop on embedded systems development with FreeRTOS will be held from October 5-7, 2024. Registration is open to all ECE students.', 0),
                    ('PhD Openings - IoT and Signal Processing', 'Looking for motivated Ph.D. students in IoT systems and signal processing. Minimum qualification: GATE score above 600 or equivalent. Send your CV to my email.', 1),
                ]
                for title, content, important in announcements:
                    db.execute(
                        'INSERT INTO announcements (faculty_id, title, content, is_important) VALUES (?,?,?,?)',
                        (fid, title, content, important)
                    )

        db.commit()
        print("Database seeded successfully with 2 faculty members.")
        print("Admin login: admin / admin123")
        print("Faculty logins: anand / anand123, sunita / sunita123")

if __name__ == '__main__':
    seed()
