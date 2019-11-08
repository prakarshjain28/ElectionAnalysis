package com.example.electionanalysis;

import androidx.appcompat.app.AppCompatActivity;

import android.content.Intent;
import android.os.Bundle;
import android.view.View;
import android.widget.Button;

import com.google.firebase.firestore.FirebaseFirestore;
import com.google.firebase.firestore.core.FirestoreClient;

public class MainActivity extends AppCompatActivity implements View.OnClickListener {
    private FirebaseFirestore db;
    Button b1,b2;
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
        db=FirebaseFirestore.getInstance();
        b1=(Button)findViewById(R.id.graph);
        b2=(Button)findViewById(R.id.senti);
        b1.setOnClickListener(this);
        b2.setOnClickListener(this);
    }

    @Override
    public void onClick(View v) {
        if(v==b1){
            Intent intent=new Intent(getBaseContext(),GraphActivity.class);
            startActivity(intent);
        }
        if(v==b2){
            Intent intent=new Intent(getBaseContext(),PieActivity.class);
            startActivity(intent);
        }
    }
}
