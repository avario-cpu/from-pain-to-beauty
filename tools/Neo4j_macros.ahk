#Persistent
#NoEnv
#SingleInstance force
SetTitleMatchMode, 2 ; Allows for partial matching of the window title

targetWindowTitle := "neo4j@bolt://localhost:7687/neo4j - Neo4j Browser"

MatchNodeSingle() {
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

MatchRelationshipSingle() {
    SendInput, MATCH(xx)-[rr]->(yy)
    SendInput, {End}{Shift down}{Enter}{Shift up}WHERE apoc.rel.id(rr)=
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
    SendInput, MATCH pp=(xx)-[rr*1..3]->(yy)
    SendInput, {Shift down}{Enter}{Shift up}WHERE apoc.node.id(xx)=
    SendInput, {Shift down}{Enter}{Shift up}RETURN pp
    SendInput, {Up}{End}
}

MatchPathNodeIn(){
    SendInput, MATCH pp=(xx)-[rr*1..3]->(yy)
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

HandleRelationshipInput(input) {
    if (GetKeyState("Shift", "P") && !GetKeyState("Alt", "P")) {
        if (input = "lo") {
            return "IS_LOCKED"
        } else if (input = "th") {
            return "THEN"
        } else if (input = "if") {
            return "IF"
        }
    } else if (GetKeyState("Shift", "P") && GetKeyState("Alt", "P")) {
        if (input = "lo") {
            return "AND_IS_LOCKED"
        }
    } else {
        if (input = "al") {
            return "ALLOWS"
        } else if (input = "ap") {
            return "APPLIES"
        } else if (input = "at") {
            return "ATTEMPTS"
        } else if (input = "ch") {
            return "CHECKS"
        } else if (input = "de") {
            return "DEFAULTS"
        } else if (input = "di") {
            return "DISABLES"
        } else if (input = "ex") {
            return "EXPECTS"
        } else if (input = "in") {
            return "INITIATES"            
        } else if (input = "li") {
            return "LISTENS"
        } else if (input = "lo") {
            return "LOCKS"
        } else if (input = "pr") {
            return "PRIMES"
        } else if (input = "re") {
            return "REVERTS"
        } else if (input = "tr") {
            return "TRIGGERS"
        } else if (input = "un") {
            return "UNLOCKS"
        }
    }  
        return input
    
}

HandleNodeInput(input) {
    if (input = "an") {
        return "Answer"
    } else if (input = "in") {
        return "Input"
    } else if (input = "lo") {
        return "LogicGate"
    } else if (input = "ou") {
        return "Output"
    } else if (input = "pr") {
        return "Prompt"
    } else if (input = "qu") {
        return "Question"
    } else if (input = "tr") {
        return "TrafficGate"
    } else if (input = "re") {
        return "Response"
    } else if (input = "wh") {
        return "Whisper"
    } else {
        return input
    }
}



^+m:: ; Matches Hotkey: Ctrl+Shift+M
    if WinActive(targetWindowTitle) {
        Input, NextKey, L2
        if (NextKey = "ns") {
            MatchNodeSingle()
        } else if (NextKey = "nl") {
            MatchNodeLabel()
        } else if (NextKey = "rs") {
            MatchRelationshipSingle()
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
    }
return


^+c:: ; Creations Hotkey: Ctrl+Shift+C
    if WinActive(targetWindowTitle) {
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
    }
return

^+s:: ; Set Hotkey: Ctrl+Shift+S 
    if WinActive(targetWindowTitle) {
        Input, NextKey, L1
        if (NextKey = "t") {
            SetText()
        }
    }
return

^+r:: ; Write return : Ctrl+Shift+D
    if WinActive(targetWindowTitle) {
        SendInput, RETURN{Space}
    }
return

^+d:: ; Write delete : Ctrl+Shift+D
    if WinActive(targetWindowTitle) {
        SendInput, DELETE{Space}
    }
return

+!d:: ; Write detach delete : Shift+Alt+D
    if WinActive(targetWindowTitle) {
        SendInput, DETACH DELETE{Space}
    }
return

^+w:: ; With * Hotkey: Ctrl+Shift+*
    if WinActive(targetWindowTitle) {
        SendInput,WITH *{Shift down}{Enter}{Shift up}
    }
return

^w:: ; Simply here to overwrite CltrW exit window to avoid accidents
return

^+\:: ; Return all Hotkey: Ctrl+Shift+\
    if WinActive(targetWindowTitle) {
        SendInput,^{End}{Shift down}{Enter}{Shift up}WITH *{Shift down}{Enter}{Shift up}MATCH(all){Shift down}{Enter}{Shift up}RETURN all
    }
return

^+BackSpace:: ; Return Hotkey: Ctrl+Shift+Backspace
    if WinActive(targetWindowTitle) {
        SendInput,^{End}{Shift down}{Enter}{Shift up}RETURN{Space}
    }
return
