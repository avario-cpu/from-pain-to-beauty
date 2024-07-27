#Persistent
#NoEnv
#SingleInstance force
SetTitleMatchMode, 2 ; Allows for partial matching of the window title

targetWindowTitle := "neo4j@bolt://localhost:7687/neo4j - Neo4j Browser"

MatchNodeAlias() {
    SendInput, MATCH(
    Input, UserInput, L3
    SendInput, %UserInput%){Shift down}{Enter}{Shift up}WHERE apoc.node.id(%UserInput%)=
}

MatchNodeLabel() {
    SendInput, MATCH(xxx:)-[rrr]->(yyy)
    SendInput {Shift down}{Enter}{Shift up}RETURN xxx,rrr,yyy
    Send, {Up}^{Left}^{Left}^{Left}{Right}
    Input, Input1, L3
    SendInput, % HandleNodeInput(Input1)
}


MatchRelationshipAlias() {
    SendInput, MATCH()-[]->()
    SendInput, {Left 5}
    Input, Input1, L3
    SendInput, %Input1%
    SendInput, {End}{Shift down}{Enter}{Shift up}WHERE apoc.rel.id(%Input1%)=
}

MatchRelationshipType() {
    SendInput, MATCH(xxx)-[rrr:]->(yyy)
    SendInput, {Shift down}{Enter}{Shift up}RETURN xxx,rrr,yyy
    Send, {Up}{left}
    Input, Input1, L3
    SendInput, % HandleRelationshipInput(Input1)
}

MatchRelationshipNodes() {
    SendInput, MATCH()-[]->()
    Send, ^{Left}{Right}
    Input, Input1, L3
    SendInput, %Input1%
    Send, ^{Right}{Left}
    Input, Input2, L3
    SendInput, %Input2%
    Send, ^{Left}^{Left}{Right 3}
    Input, Input3, L3
    SendInput, %Input3%
    Send, {Right}
    Send, {End}{Shift down}{Enter}{Shift up}WHERE apoc.rel.id(%Input3%)=
}

MatchPropertyKey() {
    SendInput, MATCH (xxx)-[rrr]->(yyy)
    SendInput, {Shift down}{Enter}{Shift up}WHERE any(key IN keys(rrr) WHERE key = "")
    SendInput, {Shift down}{Enter}{Shift up}RETURN xxx,rrr,yyy
    SendInput, {Up}{End}{Left 2}
}

MatchPathNodeOut(){
    SendInput, MATCH ppp=(xxx)-[rrr*1..5]->(yyy)
    SendInput, {Shift down}{Enter}{Shift up}WHERE apoc.node.id(xxx)=
    SendInput, {Shift down}{Enter}{Shift up}RETURN ppp
    SendInput, {Up}{End}
}

MatchPathNodeIn(){
    SendInput, MATCH ppp=(xxx)-[rrr*1..5]->(yyy)
    SendInput, {Shift down}{Enter}{Shift up}WHERE apoc.node.id(yyy)=
    SendInput, {Shift down}{Enter}{Shift up}RETURN ppp
    SendInput, {Up}{End}
}

MatchPathNodeAll(){
    SendInput, MATCH ppp=(xxx)-[rrr*1..3]-(yyy)
    SendInput, {Shift down}{Enter}{Shift up}WHERE apoc.node.id(xxx)=
    SendInput, {Shift down}{Enter}{Shift up}RETURN ppp
    SendInput, {Up}{End}
}


MatchPathLabel(){
    SendInput, MATCH ppp=(xxx)-[rrr*1..3]->(yyy)
    SendInput, {Shift down}{Enter}{Shift up}WHERE apoc.node.id(xxx)=
    SendInput, {Shift down}{Enter}{Shift up}WITH p, [n IN nodes(p) WHERE "" IN labels(n)] AS matchNodes
    Loop, 6
    {
        Send, ^{Left}
        Sleep, 10
    }
    Send, {Left 2}
    Input, Input2, L3
    SendInput, % HandleNodeInput(Input2)
    SendInput, {End}{Shift down}{Enter}{Shift up}UNWIND matchNodes AS xxx
    SendInput, {Up 2}{End}
}


CreateNode() {
    SendInput, CREATE(
    Input, Input1, L3
    SendInput, %Input1%:
        Input, Input2, L3
        SendInput, % HandleNodeInput(Input2)
        SendRaw, {text:""}
        Send, {Left 2}
    }

CreateRelationshipAlias() {
    SendInput, CREATE()-[:]->()
    Send, ^{Left}{Right}
    Input, Input1, L3
    SendInput, %Input1%
    Send, ^{Right}{Left}
    Input, Input2, L3
    SendInput, %Input2%
    Send, ^{Left}^{Left}{Right 3}
    Input, Input3, L3
    SendInput, %Input3%
    Send, {Right}
    Input, Input4, L3
    SendInput, % HandleRelationshipInput(Input4)
    Send, {End}{Shift down}{Enter}{Shift up}
}


CreateRelationshipNoLabel() {
    SendInput, CREATE()-[:]->()
     Send, ^{Left}{Right}
    Input, Input1, L3
    SendInput, %Input1%
    Send, ^{Right}{Left}
    Input, Input2, L3
    SendInput, %Input2%
    Send, ^{Left}{Left 4}
    Input, Input3, L3
    SendInput, % HandleRelationshipInput(Input3)
    Send, {End}{Shift down}{Enter}{Shift up}
}

CreateRelationshipReplace(){
    SendInput, MATCH(xxx)-[rrr]->(yyy)
    SendInput, {Shift down}{Enter}{Shift up}WHERE apoc.rel.id(rrr)=
    SendInput, {Shift down}{Enter}{Shift up}DELETE rrr
    SendInput, {Shift down}{Enter}{Shift up}WITH *
    SendInput, {Shift down}{Enter}{Shift up}CREATE(xxx)-[:]->(yyy)
    SendInput, ^{Left}{Left 4}
    Input, Input1, L3
    SendInput, % HandleRelationshipInput(Input1)
    SendInput, {End}{Up 3}
}

SetText() {
    SendInput, set{space}
    Input, Input1, L3
    SendInput, %Input1%.text=""
    Send, {Left}
}

SetRandomWeight(){
    SendInput, set{space}
    Input, Input1, L3
    SendInput, %Input1%.randomWeight=
}

SetDuration(){
    SendInput, set{space}
    Input, Input1, L3
    SendInput, %Input1%.duration=
}

HandleRelationshipInput(user_input) {
    if (GetKeyState("Shift", "P") && !GetKeyState("Alt", "P")) {
        if (user_input = "loc") {
            return "IS_LOCKED"
        }
    } else if (GetKeyState("Shift", "P") && GetKeyState("Alt", "P")) {
        if (user_input = "loc") {
            return "AND_IS_LOCKED"
        }
    } else {
        if (user_input = "all") {
            return "ALLOWS"
        } else if (user_input = "the") {
            return "THEN"
        } else if (user_input = "act") {
            return "ACTIVATES"
        } else if (user_input = "iff") {
            return "IF"
        } else if (user_input = "app") {
            return "APPLIES"
        } else if (user_input = "att") {
            return "ATTEMPTS"
        } else if (user_input = "che") {
            return "CHECKS"
        } else if (user_input = "def") {
            return "DEFAULTS"
        } else if (user_input = "dis") {
            return "DISABLES"
        } else if (user_input = "exp") {
            return "EXPECTS"
        } else if (user_input = "ini") {
            return "INITIATES"            
        } else if (user_input = "lis") {
            return "LISTENS"
        } else if (user_input = "loc") {
            return "LOCKS"
        } else if (user_input = "pri") {
            return "PRIMES"
        } else if (user_input = "rev") {
            return "REVERTS"
        } else if (user_input = "tri") {
            return "TRIGGERS"
        } else if (user_input = "unl") {
            return "UNLOCKS"
        } else if (user_input = "cut") {
            return "CUTSOFF"
        } else if (user_input = "per") {
            return "PERMITS"
        }
    }
    return user_input
}

HandleNodeInput(user_input) {
    if (user_input = "ans") {
        return "Answer"
    } else if (user_input = "inp") {
        return "Input"
    } else if (user_input = "log") {
        return "LogicGate"
    } else if (user_input = "out") {
        return "Output"
    } else if (user_input = "pro") {
        return "Prompt"
    } else if (user_input = "que") {
        return "Question"
    } else if (user_input = "tra") {
        return "TrafficGate"
    } else if (user_input = "res") {
        return "Response"
    } else if (user_input = "ple") {
        return "Plea"
    } else if (user_input = "whi") {
        return "Whisper"
    } else {
        return user_input
    }
}



#If WinActive(targetWindowTitle)
^+m:: ; Matches Hotkey: Ctrl+Shift+M
    Input, NextKey, L3
    if (NextKey = "nal") {
        MatchNodeAlias()
    } else if (NextKey = "nla") {
        MatchNodeLabel()
    } else if (NextKey = "ral") {
        MatchRelationshipAlias()
    } else if (NextKey = "rty") {
        MatchRelationshipType()
    } else if (NextKey = "rno") {
        MatchRelationshipNodes()
    } else if (NextKey = "pke") {
        MatchPropertyKey()
    } else if (NextKey = "pat") {
         Input, UserInput, L3
         if (UserInput = "nou"){
            MatchPathNodeOut()
        } else if (UserInput = "nin"){
            MatchPathNodeIn()
        } else if(UserInput = "lab"){
            MatchPathLabel()
        } else if(UserInput = "nal"){
            MatchPathNodeAll()
        }
    }
return


^+c:: ; Creations Hotkey: Ctrl+Shift+C
    Input, NextKey, L3
    if (NextKey = "nal") {
        CreateNode()
    } else if (NextKey = "rnl") {
            CreateRelationshipNoLabel()
    } else if (NextKey = "ral") {
            CreateRelationshipAlias()
    } else if (NextKey = "rrp") {
            CreateRelationshipReplace()
    } 
return

targetWindowTitle := "Your Window Title Here"

^+s:: ; Set Hotkey: Ctrl+Shift+S 
    Input, NextKey, L3
    if (NextKey = "tex") {
        SetText()
    } else if (NextKey = "rwe") {
        SetRandomWeight()
    } else if (NextKey = "dur") {
        SetDuration()
    }
return

^+r:: ; Write return : Ctrl+Shift+D
    SendInput, RETURN{Space}
return

^+u:: ; Write UNWIND as : Ctrl+Shift+D
     SendInput, UNWIND  AS
     Send, ^{Left}{Left}
     Input, UserInput, L3
     Send, %USerInput%
     Send, ^{Right}{Space}
return

^+d:: ; Write delete : Ctrl+Shift+D
    SendInput, DELETE{Space}
return

+!d:: ; Write detach delete : Shift+Alt+D
    SendInput, DETACH DELETE{Space}
return

^+w:: ; With * Hotkey: Ctrl+Shift+*
    SendInput,WITH *{Shift down}{Enter}{Shift up}
return

^w:: ; Simply here to overwrite CltrW exit window to avoid accidents
return

^+\:: ; Return all Hotkey: Ctrl+Shift+\
    SendInput,^{End}{Shift down}{Enter}{Shift up}WITH *{Shift down}{Enter}{Shift up}MATCH(everything){Shift down}{Enter}{Shift up}RETURN everything
return

^+BackSpace:: ; Return Hotkey: Ctrl+Shift+Backspace
    SendInput,^{End}{Shift down}{Enter}{Shift up}RETURN{Space}
return

#If