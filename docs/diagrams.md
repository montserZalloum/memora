graph TD
    %% المرحلة الأولى: التأسيس والمحتوى
    subgraph Stage_1 [Stage 1: Content & Foundation]
        A[Memora Grade/Stream/Season] --> B[Memora Subject]
        B --> C[Memora Track/Unit/Topic]
        C --> D[Memora Lesson]
        D --> E[Memora Lesson Stage - JSON Data]
    end

    %% المرحلة الثانية: التخطيط والتسعير
    subgraph Stage_2 [Stage 2: Business & Planning]
        F[Memora Academic Plan] --> G[Memora Plan Subject]
        G --> H{Memora Plan Override}
        H -- Hide/Show Logic --> F
        I[ERPNext Item / Pricing] <--> J[Memora Product Grant]
        J -- Grants Access To --> F
    end

    %% المرحلة الثالثة: رحلة الطالب والاشتراك
    subgraph Stage_3 [Stage 3: Player Onboarding]
        K[Frappe User] --> L[Memora Player Profile]
        L --> M[Memora Player Wallet]
        L --> N[Memora Player Device]
        O[Memora Subscription Transaction] -- Success --> J
        O -- Triggers --> P[Memora Structure Progress - Init]
    end

    %% المرحلة الرابعة: محرك اللعب والذاكرة
    subgraph Stage_4 [Stage 4: FSRS & Gameplay Loop]
        E --> Q[Player Interaction / Question]
        Q --> R[Memora Interaction Log]
        R --> S{FSRS Engine}
        S --> T[Memora Memory State - Intervals]
        S --> U[Memora Structure Progress - Update]
        U --> V[Memora Player Wallet - XP/Streak]
    end

    %% المرحلة الخامسة: الصيانة
    subgraph Stage_5 [Stage 5: Feedback Loop]
        Q -- Report Error --> W[Memora Content Report]
        W -- Alert --> B
    end

    %% الربط بين المراحل
    E -.-> Q
    F -.-> P
    J -.-> P

************
Structure Diagram (ERD-like)
graph TD

    %% 1. الهيكل التنظيمي (The Hierarchy)
    subgraph Content_Hierarchy [Content Hierarchy]
        Grade[Memora Grade] --- Stream[Memora Stream]
        Stream --- Season[Memora Season]
        Season --- Subject[Memora Subject]
        Subject --- Track[Memora Track]
        Track --- Unit[Memora Unit]
        Unit --- Topic[Memora Topic]
        Topic --- Lesson[Memora Lesson]
        Lesson --- Stage[Memora Lesson Stage]
    end

    %% 2. نظام التخطيط (The Academic Mapping)
    subgraph Academic_Layer [Academic Planning Layer]
        Plan[Memora Academic Plan]
        PlanSubject[Memora Plan Subject]
        Override[Memora Plan Override]
        
        Plan --- PlanSubject
        Plan --- Override
        PlanSubject -.-> Subject
        Override -.-> Unit
        Override -.-> Lesson
    end

    %% 3. نظام البيع والصلاحيات (Monetization & Access)
    subgraph Access_System [Monetization & Grants]
        Trans[Memora Subscription Transaction]
        Grant[Memora Product Grant]
        Comp[Memora Grant Component]
        
        Trans --> Grant
        Grant --- Comp
        Comp -.-> Plan
        Comp -.-> Track
    end

    %% 4. بيانات اللاعب (Player Data)
    subgraph Player_Domain [Player & Progress]
        User((Frappe User))
        Profile[Memora Player Profile]
        Wallet[Memora Player Wallet]
        Device[Memora Player Device]
        
        User --- Profile
        Profile --- Wallet
        Profile --- Device
    end

    %% 5. المحرك الديناميكي (Dynamic Engine)
    subgraph Performance_Engine [Tracking & FSRS]
        Progress[Memora Structure Progress]
        MemState[Memora Memory State]
        Log[Memora Interaction Log]
        Report[Memora Content Report]
        
        Progress -.-> Profile
        Progress -.-> Lesson
        
        MemState -.-> Profile
        MemState -.-> Lesson
        
        Log -.-> Profile
        Log -.-> Stage
        
        Report -.-> Lesson
    end

    %% Key Connections
    Plan -.-> Grade
    Plan -.-> Stream