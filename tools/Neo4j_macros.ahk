#Persistent
#NoEnv
#SingleInstance force
SetTitleMatchMode, 2 ; Allows for partial matching of the window title

targetWindowTitle := "neo4j@bolt://localhost:7687/neo4j - Neo4j Browser"

MatchNodeAlias() {
    SendInput, MATCH(
    Input, UserInput, L2
    SendInput, %UserInput%){Shift down}{Enter}{Shift up}WHERE apoc.node.id(%UserInput%)=
}

MatchNodeLabel() {
    SendInput, MATCH(xx:)-[rr]->(yy)
    SendInput {Shift down}{Enter}{Shift up}RETURN xx,rr,yy
    Send, {Up}{Left 5}
    Input, Input1, L2
    SendInput, % HandleNodeInput(Input1)
}


MatchRelationshipAlias() {
    SendInput, MATCH()-[]->()
    SendInput, {Left 5}
    Input, Input1, L2
    SendInput, %Input1%
    SendInput, {End}{Shift down}{Enter}{Shift up}WHERE apoc.rel.id(%Input1%)=
}

MatchRelationshipType() {
    SendInput, MATCH(xx)-[rr:]->(yy)
    SendInput, {Shift down}{Enter}{Shift up}RETURN xx,rr,yy
    Send, {Up}{left}
    Input, Input1, L2
    SendInput, % HandleRelationshipInput(Input1)
}

MatchRelationshipNodes() {
    SendInput, MATCH()-[]->()
    Send, ^{Left}{Right}
    Input, Input1, L2
    SendInput, %Input1%
    Send, ^{Right}{Left}
    Input, Input2, L2
    SendInput, %Input2%
    Send, ^{Left}^{Left}{Right 3}
    Input, Input3, L2
    SendInput, %Input3%
    Send, {Right}
    Send, {End}{Shift down}{Enter}{Shift up}WHERE apoc.rel.id(%Input3%)=
}

MatchPropertyKey() {
    SendInput, MATCH (xx)-[rr]->(yy)
    SendInput, {Shift down}{Enter}{Shift up}WHERE any(key IN keys(r) WHERE key = "")
    SendInput, {Shift down}{Enter}{Shift up}RETURN xx,rr,y
    SendInput, {Up}{End}{Left 2}
}

MatchPathNodeOut(){
    SendInput, MATCH pp=(xx)-[rr*1..5]->(yy)
    SendInput, {Shift down}{Enter}{Shift up}WHERE apoc.node.id(xx)=
    SendInput, {Shift down}{Enter}{Shift up}RETURN pp
    SendInput, {Up}{End}
}

MatchPathNodeIn(){
    SendInput, MATCH pp=(xx)-[rr*1..5]->(yy)
    SendInput, {Shift down}{Enter}{Shift up}WHERE apoc.node.id(yy)=
    SendInput, {Shift down}{Enter}{Shift up}RETURN pp
    SendInput, {Up}{End}
}

MatchPathNodeAll(){
    SendInput, MATCH pp=(xx)-[rr*1..3]-(yy)
    SendInput, {Shift down}{Enter}{Shift up}WHERE apoc.node.id(xx)=
    SendInput, {Shift down}{Enter}{Shift up}RETURN pp
    SendInput, {Up}{End}
}


MatchPathLabel(){
    SendInput, MATCH pp=(xx)-[rr*1..3]->(yy)
    SendInput, {Shift down}{Enter}{Shift up}WHERE apoc.node.id(xx)=
    SendInput, {Shift down}{Enter}{Shift up}WITH p, [n IN nodes(p) WHERE "" IN labels(n)] AS matchNodes
    Loop, 6
    {
        Send, ^{Left}
        Sleep, 10
    }
    Send, {Left 2}
    Input, Input2, L2
    SendInput, % HandleNodeInput(Input2)
    SendInput, {End}{Shift down}{Enter}{Shift up}UNWIND matchNodes AS xx
    SendInput, {Up 2}{End}
}


CreateNode() {
    SendInput, CREATE(
    Input, Input1, L2
    SendInput, %Input1%:
        Input, Input2, L2
        SendInput, % HandleNodeInput(Input2)
        SendRaw, {text:""}
        Send, {Left 2}
    }

CreateRelationship() {
    SendInput, CREATE()-[:]->()
    Send, ^{Left}{Right}
    Input, Input1, L2
    SendInput, %Input1%
    Send, ^{Right}{Left}
    Input, Input2, L2
    SendInput, %Input2%
    Send, ^{Left}^{Left}{Right 3}
    Input, Input3, L2
    SendInput, %Input3%
    Send, {Right}
    Input, Input4, L2
    SendInput, % HandleRelationshipInput(Input4)
    Send, {End}{Shift down}{Enter}{Shift up}
}

CreateRelationshipNoLabel() {
    SendInput, CREATE()-[:]->()
     Send, ^{Left}{Right}
    Input, Input1, L2
    SendInput, %Input1%
    Send, ^{Right}{Left}
    Input, Input2, L2
    SendInput, %Input2%
    Send, ^{Left}{Left 4}
    Input, Input3, L2
    SendInput, % HandleRelationshipInput(Input3)
    Send, {End}{Shift down}{Enter}{Shift up}
}

SetText() {
    SendInput, set{space}
    Input, Input1, L2
    SendInput, %Input1%.text=""
    Send, {Left}
}

SetRandomWeight(){
    SendInput, set{space}
    Input, Input1, L2
    SendInput, %Input1%.randomWeight=
}

SetDuration(){
    SendInput, set{space}
    Input, Input1, L2
    SendInput, %Input1%.duration=
}

HandleRelationshipInput(user_input) {
    if (GetKeyState("Shift", "P") && !GetKeyState("Alt", "P")) {
        if (user_input = "lo") {
            return "IS_LOCKED"
        } else if (user_input = "th") {
            return "THEN"
        } else if (user_input = "if") {
            return "IF"
        }
    } else if (GetKeyState("Shift", "P") && GetKeyState("Alt", "P")) {
        if (user_input = "lo") {
            return "AND_IS_LOCKED"
        }
    } else {
        if (user_input = "al") {
            return "ALLOWS"
        } else if (user_input = "ap") {
            return "APPLIES"
        } else if (user_input = "at") {
            return "ATTEMPTS"
        } else if (user_input = "ch") {
            return "CHECKS"
        } else if (user_input = "de") {
            return "DEFAULTS"
        } else if (user_input = "di") {
            return "DISABLES"
        } else if (user_input = "ex") {
            return "EXPECTS"
        } else if (user_input = "in") {
            return "INITIATES"            
        } else if (user_input = "li") {
            return "LISTENS"
        } else if (user_input = "lo") {
            return "LOCKS"
        } else if (user_input = "pr") {
            return "PRIMES"
        } else if (user_input = "re") {
            return "REVERTS"
        } else if (user_input = "tr") {
            return "TRIGGERS"
        } else if (user_input = "un") {
            return "UNLOCKS"
        } else if (user_input = "cu") {
            return "CUTSOFF"
        }
    }
    return user_input
}

HandleNodeInput(user_input) {
    if (user_input = "an") {
        return "Answer"
    } else if (user_input = "in") {
        return "Input"
    } else if (user_input = "lo") {
        return "LogicGate"
    } else if (user_input = "ou") {
        return "Output"
    } else if (user_input = "pr") {
        return "Prompt"
    } else if (user_input = "qu") {
        return "Question"
    } else if (user_input = "tr") {
        return "TrafficGate"
    } else if (user_input = "re") {
        return "Response"
    } else if (user_input = "wh") {
        return "Whisper"
    } else {
        return user_input
    }
}


#If WinActive(targetWindowTitle)
^+m:: ; Matches Hotkey: Ctrl+Shift+M
    Input, NextKey, L2
    if (NextKey = "na") {
        MatchNodeAlias()
    } else if (NextKey = "nl") {
        MatchNodeLabel()
    } else if (NextKey = "ra") {
        MatchRelationshipAlias()
    } else if (NextKey = "rt") {
        MatchRelationshipType()
    } else if (NextKey = "rn") {
        MatchRelationshipNodes()
    } else if (NextKey = "pk") {
        MatchPropertyKey()
    } else if (NextKey = "pa") {
         Input, UserInput, L2
         if (UserInput = "no"){
            MatchPathNodeOut()
        } else if (UserInput = "ni"){
            MatchPathNodeIn()
        } else if(UserInput = "la"){
            MatchPathLabel()
        } else if(UserInput = "na"){
            MatchPathNodeAll()
        }
    }

return


^+c:: ; Creations Hotkey: Ctrl+Shift+C
    Input, NextKey, L1
    if (NextKey = "n") {
        CreateNode()
    } else if (NextKey = "r") {
        if GetKeyState("Shift", "P") {
            CreateRelationshipNoLabel()
        } else {
            CreateRelationship()
        }
    }
    
return

targetWindowTitle := "Your Window Title Here"

^+s:: ; Set Hotkey: Ctrl+Shift+S 
    Input, NextKey, L2
    if (NextKey = "te") {
        SetText()
    } else if (NextKey = "rw") {
        SetRandomWeight()
    } else if (NextKey = "du") {
        SetDuration()
    }
    
return

^+r:: ; Write return : Ctrl+Shift+D
    SendInput, RETURN{Space}
return

^+u:: ; Write UNWIND as : Ctrl+Shift+D
     SendInput, UNWIND  AS
     Send, ^{Left}{Left}
     Input, UserInput, L2
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
    SendInput,^{End}{Shift down}{Enter}{Shift up}WITH *{Shift down}{Enter}{Shift up}MATCH(all){Shift down}{Enter}{Shift up}RETURN all
return

^+BackSpace:: ; Return Hotkey: Ctrl+Shift+Backspace
    SendInput,^{End}{Shift down}{Enter}{Shift up}RETURN{Space}
return

#If